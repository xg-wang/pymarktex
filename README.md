# Pymarktex

I am used to write markdown files for quick notes and documents, however the group meeting in the lab requires LaTeX files to be deposited.

This project is for converting a *Markdown* file into a *LaTeX* file, thus valuable time could be saved.

*notice*
this is not a complete converter since it is hard to convert some of the corner syantax of markdown, but insert the LaTeX snippets of the notes still counts.

This module is inspired by [mistune](http://mistune.readthedocs.org/).

## Usage
Usage:

    ./pymarktex.py textfile.md

or:

    import pymarktex
    somelatex = pymarktex.parse(sometext)

## Supported syntax
Replace the following:

- `**emphasize**` or `__emphasize__`
- `*italic*` or `_italic_`
- atx style`# header` or Setext style`===` and `---`
- item by `*` or `+` or `-`
- enum by `1.`, does not matter which number
- `[link](http://example.com/)` or `<http:example.com/>`, ref style not support
- `![img](/path/img.jpg)`
- `inline code`
- block code with 4 tabs or enclosed ````/~~~`
- `> quotations`
- hrule: `---`

into latex format:

- `\textbf{emphasize}`
- `\textit{italic}`
- `\section{header}` and `{subsection}` for `##/---`
- `\begin{itemize}\n...\item \n...\end{itemize}`
- `\begin{enumerate}\n...\item \n...\end{enumerate}`
- `\href{http://example.com/}{link}`
- figure blocks

    ```
    \begin{figure}[htbp]
      \centering
      \includegraphics[width=0.8\textwidth]{/path/img.jpg}
      \caption{img}
      \label{fig:img}
    \end{figure}
    ```

- `\lstinline{inline code}`
- `\begin{lstlisting}[language=Python]...\end{lstlisting}`
- `\begin{quotation} ... \end{quotation}`
- hrule treated as `\newpage`

## TODO list
- fix escape charactors
- fix `<link>` bug
- prettify the nested lists output
- test suite
- more syntax
