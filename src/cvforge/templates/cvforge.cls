% cvforge.cls — a one-column CV class used by CV Forge.
% Works with pdfLaTeX (Overleaf's default), XeLaTeX, LuaLaTeX and Tectonic.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{cvforge}[2026/11/17 CV Forge class]

\LoadClass[10pt]{article}

\RequirePackage{iftex}
\ifPDFTeX
  \RequirePackage[T1]{fontenc}
  \RequirePackage[utf8]{inputenc}
  \RequirePackage{tgheros}
  \renewcommand{\familydefault}{\sfdefault}
\else
  \RequirePackage{fontspec}
  \setmainfont{texgyreheros}[
    Extension = .otf,
    UprightFont = *-regular,
    BoldFont = *-bold,
    ItalicFont = *-italic,
    BoldItalicFont = *-bolditalic]
\fi

\RequirePackage[a4paper, margin=1.6cm, top=1.4cm, bottom=1.4cm]{geometry}
\RequirePackage[dvipsnames]{xcolor}
\RequirePackage{enumitem}
\RequirePackage{tabularx}
\RequirePackage[hidelinks, unicode]{hyperref}

\definecolor{cvaccent}{HTML}{1F4E79}
\definecolor{cvmuted}{HTML}{5A5A5A}

\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\linespread{1.05}

% \cv@ifempty{text}{when empty}{otherwise}
% Uses no & characters, so it is safe inside tables (unlike the classic \ifx&#1&).
\newcommand\cv@ifempty[1]{%
  \if\relax\detokenize{#1}\relax\expandafter\@firstoftwo\else\expandafter\@secondoftwo\fi}

% ---------------------------------------------------------------- header
% \cvheader{Name}{Headline}{contact line}
\newcommand{\cvheader}[3]{%
  {\fontsize{22}{24}\selectfont\bfseries\color{cvaccent}#1\par}
  \vspace{2pt}
  \cv@ifempty{#2}{}{{\large #2\par}\vspace{3pt}}%
  {\small\color{cvmuted}#3\par}
  \vspace{6pt}
}
\newcommand{\cvsep}{\enspace\textbullet\enspace}

% ---------------------------------------------------------------- sections
\newcommand{\cvsection}[1]{%
  \vspace{8pt}
  {\color{cvaccent}\bfseries\MakeUppercase{#1}}\par
  \vspace{1pt}{\color{cvaccent}\hrule height 0.6pt}\vspace{4pt}
}

% \cventry{Title}{Organisation}{Location}{Dates}{Note}
\newcommand{\cventry}[5]{%
  \begin{tabularx}{\linewidth}{@{}X r@{}}
    \textbf{#1}\cv@ifempty{#2}{}{, #2} & {\small\color{cvmuted}#4}
  \end{tabularx}\par
  \cv@ifempty{#3#5}{}{%
    {\small\itshape\color{cvmuted}#5\cv@ifempty{#3}{}{\cv@ifempty{#5}{}{\ --- }#3}\par}}%
}

\newenvironment{cvbullets}{%
  \begin{itemize}[leftmargin=1.1em, itemsep=0pt, topsep=1pt, parsep=0pt, label={\color{cvaccent}\textbullet}]
  \small
}{\end{itemize}\vspace{3pt}}

\newcommand{\cvtech}[1]{{\footnotesize\color{cvmuted}#1\par}\vspace{3pt}}

% \cvpair{Label}{Value} — used for skills
\newcommand{\cvpair}[2]{%
  \begin{tabularx}{\linewidth}{@{}p{3.6cm} X@{}}\textbf{#1} & #2\end{tabularx}\par\vspace{1pt}
}

\endinput
