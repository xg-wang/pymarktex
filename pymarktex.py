#!/usr/bin/env python
"""pymarktex.py: A Markdown-styled-text to LaTeX converter in Python.

Usage:
  ./pymarktex.py textfile.md

Calling:
  import pymarktex
  somelatex = pymarktex.parse(sometext)
"""

import re
import sys

__version__ = '0.0.1'
__license__ = "GNU GPL 2"
__author__ = [
  'Xingan Wang <wangxgwxg@gmail.com>',
]


class BlockGrammar(object):
    """Grammars for Block level token"""
    newline = re.compile(r'^\n+')
    block_code = re.compile(r'^( {4}[^\n]+\n*)+')
    fences_code = re.compile(
        r'^ *(`{3,}|~{3,}) *(\S+)? *\n'  # ```lang
        r'([\s\S]+?)\s*'
        r'\1 *(?:\n+|$)'  # ```
    )
    hrule = re.compile(r'^ {0,3}[-*_](?: *[-*_]){2,} *(?:\n+|$)')
    heading = re.compile(r'^ *(#{1,6}) *([^\n]+?) *#* *(?:\n+|$)')
    lheading = re.compile(r'^([^\n]+)\n *(=|-){3,} *(?:\n+|$)')
    block_quote = re.compile(r'^( *>[^\n]+(\n[^\n]+)*\n*)+')
    list_block = re.compile(
        r'^( *)([*+-]|\d+\.) [\s\S]+?'
        r'(?:'
        r'\n+(?=\1?(?:[-*_] *){3,}(?:\n+|$))'  # hrule
        r'|\n{2,}'
        r'(?! )'
        r'(?!\1(?:[*+-]|\d+\.) )\n*'
        r'|'
        r'\s*$)'
    )
    list_item = re.compile(
        r'^(( *)(?:[*+-]|\d+\.) [^\n]*'
        r'(?:\n(?!\2(?:[*+-]|\d+\.) )[^\n]*)*)',
        re.M
    )
    list_bullet = re.compile(r'^ *(?:[*+-]|\d+\.) +')
    text = re.compile(r'^[^\n]+')

class BlockLexer(object):
    """Block level lexer specified by given grammar"""

    # inspect types of block
    default_rules = [
        'newline', 'block_code', 'fences_code', 'hrule',
        'heading', 'lheading', 'block_quote',
        'list_block', 'text'
    ]
    # rules available within a list
    list_rules = [
        'newline', 'block_code', 'fences_code', 'hrule',
        'block_quote', 'list_block', 'text',
    ]

    def __init__(self, rules=None, **kwargs):
        self.tokens = []
        self.rules = rules or BlockGrammar()

        # helper re
        self._block_code_leading_pattern = re.compile(r'^ {4}', re.M)
        self._block_quote_leading_pattern = re.compile(r'^ *> ?', flags=re.M)


    def __call__(self, text, rules=None):
        return self.parse(text, rules)

    def parse(self, text, rules=None):
        text = text.rstrip('\n')
        rules = rules or self.default_rules

        def _match_by_rules(text):
            for rule in rules:
                rule_pattern = getattr(self.rules, rule)
                match = rule_pattern.match(text)
                if match:
                    getattr(self, 'parse_%s' % rule)(match)
                    return match
            return False

        while text:
            match = _match_by_rules(text)
            if match is not False:
                # if matched, parse the block to tokens and delete.
                text = text[len(match.group(0)):]
                continue
            if text:
                # not matching when text remains leads to error.
                raise RuntimeError('Infinite loop at: %s' % text)
        return self.tokens

    def parse_newline(self, m):
        if len(m.group(0)) > 1:
            self.tokens.append({'type': 'newline'})

    def parse_block_code(self, m):
        code = self._block_code_leading_pattern.sub('', m.group(0))
        self.tokens.append({
            'type': 'code',
            'lang': None,
            'text': code
        })

    def parse_fences_code(self, m):
        self.tokens.append({
            'type': 'code',
            'lang': m.group(2),
            'text': m.group(3)
        })

    def parse_hrule(self, m):
        self.tokens.append({
            'type': 'hrule'
        })

    def parse_heading(self, m):
        self.tokens.append({
            'type': 'heading',
            'level': len(m.group(1)),
            'text': m.group(2),
        })

    def parse_lheading(self, m):
        self.tokens.append({
            'type': 'heading',
            'level': 1 if m.group(2) == '=' else 2,
            'text': m.group(1),
        })

    def parse_block_quote(self, m):
        self.tokens.append({'type': 'block_quote_start'})
        # clean leading >
        quot = self._block_quote_leading_pattern.sub('', m.group(0))
        self.parse(quot)
        self.tokens.append({'type': 'block_quote_end'})

    def parse_list_block(self, m):
        bullet = m.group(2)
        self.tokens.append({
            'type': 'list_start',
            'ordered': '.' in bullet  # True if ordered
        })
        self._process_list_item(m.group(0), bullet)
        self.tokens.append({'type': 'list_end'})

    def _process_list_item(self, list, bullet):
        # find all items
        all_items = self.rules.list_item.findall(list)

        _next = False
        length = len(all_items)

        for i in range(length):
            item = all_items[i][0]

            # remove the bullet
            space = len(item)
            item = self.rules.list_bullet.sub('', item)

            # outdent
            if '\n ' in item:
                space = space - len(item)
                pattern = re.compile(r'^ {1,%d}' % space, re.M)
                item = pattern.sub('', item)

            # determine whether item is loose or not
            loose = _next
            if not loose and re.search(r'\n\n(?!\s*$)', item):
                loose = True

            rest = len(item)
            if i != length - 1 and rest:
                _next = item[rest-1] == '\n'
                if not loose:
                    loose = _next

            if loose:
                type = 'loose_item_start'
            else:
                type = 'list_item_start'

            self.tokens.append({'type': type})
            # recurse
            self.parse(item, self.list_rules)
            self.tokens.append({'type': 'list_item_end'})

    def parse_text(self, m):
        text = m.group(0)
        self.tokens.append({
            'type': 'text',
            'text': text
        })


class InlineGrammar(object):
    """Grammars  for inline level token."""
    emph = re.compile(
        r'^__([\s\S]+?)__(?!_)'  # __word__
        r'|'
        r'^\*\*([\s\S]+?)\*\*(?!_)'  # **word**
    )
    italic = re.compile(
        r'^_([\s\S]+?)_(?!_)'  # _word_
        r'|'
        r'^\*([\s\S]+?)\*(?!_)'  # *word*
    )
    link = re.compile(
        r'^!?\[('
        r'(?:\[[^^\]]*\]|[^\[\]]|\](?=[^\[]*\]))*'  # [link/img]
        r')\]\('
        r'''\s*(<)?([\s\S]*?)(?(2)>)(?:\s+['"]([\s\S]*?)['"])?\s*'''  # (url "title")
        r'\)'
    )
    inline_code = re.compile(
        r'^(`+)\s*([\s\S]*?[^`])\s*\1(?!`)'  # `code`
    )
    text = re.compile(
        r'^[\s\S]+?(?=[\\<!\[_*`~]|https?://| {2,}\n|$)'
    )

class InlineLexer(object):
    """Inline level lexer for inline grammars."""
    default_rules = [
        'emph', 'italic', 'link', 'inline_code', 'text'
    ]

    def __init__(self, renderer, rules=None, **kwargs):
        self.renderer = renderer
        self.rules = rules or InlineGrammar()

    def __call__(self, text, rules=None):
        return self.parse(text, rules)

    def parse(self, text, rules=None):
        text = text.rstrip('\n')
        rules = rules or self.default_rules

        result = self.renderer.placeholder()

        def _match_by_rules(text):
            for rule in rules:
                rule_pattern = getattr(self.rules, rule)
                match = rule_pattern.match(text)
                if match:
                    out = getattr(self, 'output_%s' % rule)(match)
                    return match, out  # terminte when match found
            return False

        while text:
            ret = _match_by_rules(text)
            if ret is not False:
                m, out = ret
                result += out
                text = text[len(m.group(0)):]
                continue
            if text:
                raise RuntimeError('Infinite loop at: %s' % text)
        return result

    def output_emph(self, m):
        text = m.group(2) or m.group(1)
        return self.renderer.emph(text)

    def output_italic(self, m):
        text = m.group(2) or m.group(1)
        return self.renderer.italic(text)

    def output_inline_code(self, m):
        code = m.group(2)
        return self.renderer.inlinecode(code)

    def output_link(self, m):
        text = m.group(1)
        link = m.group(3)
        title = m.group(4)
        if m.group(0)[0] == '!':  # is image
            return self.renderer.image(link, text, title)
        else:  # is link
            return self.renderer.link(link, text, title)

    def output_text(self, m):
        text = m.group(0)
        return self.renderer.text(text)


class Renderer(object):
    """The LaTeX renderer"""

    def __init__(self, **kwargs):
        self.options = kwargs

    def placeholder(self):
        """Return the default base output of the renderer."""
        return ''

    def newline(self):
        """ignore newline and return empty"""
        return ''

    def block_code(self, code, lang=None):
        """\begin{lstlisting}[language=<Python>]...\end{lstlisting}
        """
        code.rstrip('\n')
        output = r'\begin{lstlisting}'
        output += '[language=%s]' % lang if lang else ''
        output += '\n%s\n\end{lstlisting}\n' % code
        return output

    def hrule(self):
        """hrule treated as a newpage"""
        return '\\newpage\n'

    def header(self, text, level):
        """Render the header as sections when level < 4."""
        if level < 4:
            return '\\' + 'sub'*(level-1) + 'section{%s}\n' % text
        else:
            # just make it bold face to avoid subsubsub...
            return '\\textbf{%s}\n' % text

    def block_quote(self, text):
        """Render the quotation."""
        return '\\begin{quotation}\n%s\n\\end{quotation}\n' % text

    def emph(self, text):
        """Render the emphsized text"""
        return '\\textbf{%s}' % text

    def italic(self, text):
        """Render the italic text"""
        return '\\textit{%s}' % text

    def inlinecode(self, code):
        """Render the inline code"""
        return '\\lstinline{%s}' % code

    def text(self, text):
        """return the pure text"""
        return text

    def image(self, link, text, title=None):
        """return the image syntax"""
        # ignore title
        out = '\\begin{figure}[htbp]\n\\centering\n'
        out += '\\includegraphics[width=0.8\textwidth]{%s}\n' % link
        out += '\\caption{%s}\n\label{fig:%s}\n' % (text, text)
        out += '\\end{figure}\n'
        return out

    def link(self, link, text, title=None):
        """return the link syntax"""
        return '\\href{%s}{%s}' % (link, text)

    def list(self, text, ordered):
        """return list syntax, wrapping the body text"""
        kind = 'enumerate' if ordered else 'itemize'
        out = '\n\\begin{%s}\n%s\\end{%s}\n' % (kind, text, kind)
        return out

    def list_item(self, text):
        """return each item"""
        return '\\item\n%s\n' % text


class Markdown(object):
    """The markdown parser"""
    def __init__(self, renderer=None, inline=None, block=None, **kwargs):
        if not renderer:
            renderer = Renderer(**kwargs)
        else:
            kwargs.update(renderer.options)
        self.renderer = renderer

        self.inline = inline or InlineLexer(renderer, **kwargs)
        self.block = block or BlockLexer(BlockGrammar())
        self.tokens = []

    def __call__(self, text):
        return self.render(text)

    def render(self, text):
        return self.parse(text)

    def parse(self, text):
        text = self.normalize(text)
        return self.output(text)

    def normalize(self, text, tab=4):
        # normalize the text
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        text = text.replace('\t', ' ' * tab)
        spaceline_pattern = re.compile(r'^ +$', re.M)
        return spaceline_pattern.sub('', text)

    def output(self, text, rules=None):
        # does the major work of extracting tokens and output
        self.tokens = self.block(text, rules)
        self.tokens.reverse()
        output = self.renderer.placeholder()
        while self.pop_tokens():
            output += self.output_from_token()
        return output

    def pop_tokens(self):
        # Get the token from stack
        if not self.tokens:
            return None
        self.token = self.tokens.pop()
        return self.token

    def output_from_token(self):
        # Command pattern like way to output.
        type = self.token['type']
        return getattr(self, 'output_%s' % type)() + '\n'

    def peek(self):
        return self.tokens[-1] if self.tokens else None

    def get_all_text(self):
        # when token is text get all following texts
        text = self.token['text']
        while self.peek()['type'] == 'text':
            text += '\n' + self.pop_tokens()['text']
        return self.inline(text)

    def output_newline(self):
        return self.renderer.newline()

    def output_code(self):
        return self.renderer.block_code(
            self.token['text'], self.token['lang']
        )

    def output_hrule(self):
        return self.renderer.hrule()

    def output_heading(self):
        content = self.inline(self.token['text'])
        return self.renderer.header(
            content,
            self.token['level']
        )

    def output_block_quote_start(self):
        # render the quotation body
        quot_body = self.renderer.placeholder()
        while self.pop_tokens()['type'] != 'block_quote_end':
            quot_body += self.output_from_token()
        return self.renderer.block_quote(quot_body)

    def output_list_start(self):
        ordered = self.token['ordered']
        body = self.renderer.placeholder()
        while self.pop_tokens()['type'] != 'list_end':
            body += self.output_from_token()
        return self.renderer.list(body, ordered)

    def output_list_item_start(self):
        body = self.renderer.placeholder()
        while self.pop_tokens()['type'] != 'list_item_end':
            if self.token['type'] == 'text':
                body += self.get_all_text()
            else:
                body += self.output_from_token()
        return self.renderer.list_item(body)

    def output_loose_item_start(self):
        body = self.renderer.placeholder()
        while self.pop_tokens()['type'] != 'list_item_end':
            body += self.output_from_token()
        return self.renderer.list_item(body)

    def output_text(self):
        # output the pure text
        return self.renderer.text(self.get_all_text())



def pymarktex(text, **kwargs):
    """Render markdown formatted text to LaTeX.

    :param text: markdown formatted text content.
    :param hard_wrap: if set to True, it will use the GFM line breaks feature.
    :param parse_block_level: parse text only in block level.
    :param parse_inline_level: parse text only in inline level.
    """
    return Markdown(**kwargs)(text)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(pymarktex(open(sys.argv[1]).read()))
    else:
        print(pymarktex(sys.stdin.read()))
