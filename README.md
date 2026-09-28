# Green IT 2026 project template

Everything you submit this semester is in here. Four documents, one build command.

## First: pick your track

The short paper comes in two files, the same paper written for two kinds of object:

```
src/short-paper-mics.tex       you assess a WEB PAGE
src/short-paper-hpc.tex        you assess an HPC JOB
```

**Open the one that matches what you assess, and delete the other.** Each file carries only the
guidance its own track needs, so you never read instructions written for the other one. The build
follows whichever files are left.

## Files

```
src/short-paper-mics.tex       your short paper, web page  -> D1 (v1) and D3 (final)
src/short-paper-hpc.tex        your short paper, HPC job   -> D1 (v1) and D3 (final)
src/peer-review-1.tex          review of the first paper   -> D2
src/peer-review-2.tex          review of the second paper  -> D2
src/response-to-reviewers.tex  your reply to your reviewers -> D3
src/refs.bib                   your references, shared by every document
pdf/                           the built PDFs. This is what you upload.
webpage/                       the frozen copy of the page you study: its .html
                               and its _files/ folder. See below.
latexmkrc                      build settings. You do not need to open it.
opencode.json                  your AI coding agent's setup: the pinned model and
                               its provider order. The key that goes with it is
                               handed out in W6.
serve-frozen-copy.py           serves a frozen page the way a real server does,
                               compressed or plain, as your own site does.
                               Homework 2 asks you to use it, due Wed 30 Sep;
                               Session 4 shows you how.
localise-frozen-copy.py        brings home the files your saved page still takes
                               from the live site, so that optimising them shows
                               in your measurement. See below.
.gitignore                     keeps build noise out of your repository, and keeps
                               pdf/ in it, so your history holds the exact PDF
                               you submitted.
LICENSE                        MIT. Replace <YOUR FULL NAME> before your first commit.
```

Put your figures in `src/` as well; `\includegraphics{myfigure.png}` will find them.

## Build

One command, the same on Windows, macOS and Linux. Run it from **this** directory, not from
`src/`:

```
latexmk
```

It builds every document left in `src/` and writes `pdf/short-paper-mics.pdf` or
`pdf/short-paper-hpc.pdf`, then `pdf/peer-review-1.pdf`, `pdf/peer-review-2.pdf` and
`pdf/response-to-reviewers.pdf`.

`latexmk` ships with both TeX Live and MiKTeX, so if you can compile LaTeX at all, you already
have it. It reruns the compiler as many times as your cross-references and bibliography need,
which is why there is no build script here to get out of date.

To build just one document while you are working on it:

```
latexmk src/short-paper-mics.tex
```

Two more commands you may want:

```
latexmk -c    # delete the build artefacts, keep the PDFs
latexmk -C    # delete the build artefacts and the PDFs
```

`pdf/` holds nothing but the finished PDFs: the intermediate `.aux`, `.log` and `.bbl`
files go to `.aux/`. That is deliberate: you upload out of `pdf/`, so nothing else is allowed
to land there.

## Serve a frozen page

**Web page track.** An HPC job is frozen by pinning a commit and a fixed input instead, and
Session 3 covers that; the rest of this section is for the page.

Four steps. Run every command from **this** directory, not from `webpage/`.

**1. Freeze.** In Chrome, dismiss the cookie banner, then scroll to the bottom of the page: what
loads while you scroll is part of the page your functional unit describes, and a banner left open
freezes into the copy. Then "Save Page As…", *Web Page, Complete*, and put the `.html` file and its
`_files/` folder in `webpage/`.

**2. Bring home what the freeze left online.** The saved page still takes some of its files from
the live site: images chosen through `srcset`, SVG icon sprites, fonts named by a stylesheet. The
browser keeps fetching those from the internet, so optimising them on disk would change nothing
you measure. Run:

```
python3 localise-frozen-copy.py webpage/<your-page>.html
```

It leaves your copy untouched and writes `webpage/<your-page>-local.html` beside it, with its own
`<your-page>-local_files/` folder: every file the HTML or the CSS names on your site, its domain and
its subdomains, is downloaded there and pointed to. **The `-local` copy is the one you measure and
optimise.** Third parties stay online on purpose: analytics, consent banners, maps and chat widgets
are part of what a visitor downloads, and the script lists the ones it saw.

**3. Serve it the way your own site does.** Open your **live** page, DevTools > Network, add the
*Content-Encoding* column (right-click a column header > Response Headers), reload, and look at
the JS and CSS rows. If they show `gzip`, `br` or `zstd`, your site compresses:

```
python3 serve-frozen-copy.py 8000
```

If the column is empty, your site sends them uncompressed:

```
python3 serve-frozen-copy.py 8000 --no-gzip
```

Then open `http://localhost:8000/webpage/<your-page>-local.html`. The server serves the directory
you start it from. Measure from there. `python3 -m http.server` sends everything uncompressed
whatever your site does. Fonts and images pass through unchanged, while HTML, CSS and JavaScript
arrive three to seven times heavier, so it moves your hotspot instead of inflating a total: on
`rtl.lu`, code measured 1.2 MB compressed against 5.2 MB plain, which points the optimisation at
JavaScript on a page whose problem is a 1.07 MB PNG (eleven pages measured 2026-08-20).

**4. Check the copy.** DevTools > Network, add the *Domain* column, reload. Every row from your own
site says `localhost`; what remains is third parties and the calls scripts make while the page
runs. Reload three times. If a third party changes size between loads, right-click its row, *Block
request domain*, keep that same block for your before and your after, and list the blocked domains
in your paper. The server's terminal prints every 404: that list is what the freeze missed.

**One file, fetched twice.** If the *Domain* column shows the same file coming from `localhost`
and from its own host, your copy pays for it twice: Chrome saved the tag a script had injected,
and that script injects its own again on every load. Try

```
python3 localise-frozen-copy.py webpage/<your-page>.html --drop-injected
```

serve the copy again and compare. On `animals.sandiegozoo.org` the copy went from 12 % heavier
than the live page to 1 % (measured 2026-09-22). Keep the plain command when your page is built
by JavaScript, where the loader does not replace what the option removes.

Stop it with Ctrl+C in its terminal, or, if it runs elsewhere:

```
lsof -ti tcp:8000 | xargs kill
```

## The short paper compiles as shipped

So do the other documents. Build it once before you write anything: if `latexmk` works today, then
any later failure is something you just changed, which is a much smaller problem to debug the
evening before a deadline.

Minimum 4 double-column pages for the paper, excluding appendices and references.

## Note for AI coding agents

Build with `latexmk` from this directory. Do not write a build script and do not call `pdflatex`
directly: the settings in `latexmkrc` are what make the build reproducible, and `latexmk` handles
the reruns. Every document compiles with pdfLaTeX; they need no XeLaTeX and no LuaLaTeX.
`src/short-paper-mics.tex` and `src/short-paper-hpc.tex` are two tracks of the same paper and the
author writes one of them, so do not merge them and do not restore a file the author deleted.

Sources are in `src/`, output goes to `pdf/`. `latexmkrc` puts `src/` on `TEXINPUTS` and
`BIBINPUTS`, which is why `\bibliography{refs}` resolves to `src/refs.bib`. Do not "fix" those
paths to point at `src/` explicitly, it will break the build.
