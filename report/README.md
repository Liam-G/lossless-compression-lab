# Report

Read in order, or jump to the chapter you care about. Each chapter starts with its question and a one-paragraph
answer, then shows one diagram of the method, one chart of the results, the table behind the chart, and why it
came out that way.

| | Chapter | One-line answer |
|---|---|---|
| 0 | [Lossless compression in five minutes](0-how-to-read.md) | Two ways to compress, how to compare, and the counting argument. |
| 1 | [Can a file be regenerated from a short formula?](1-formulas.md) | No: searches find as many bits by luck as they cost to name. |
| 2 | [Do automata and matrix factors expose hidden structure?](2-dynamics.md) | Only in data built that way. |
| 3 | [Does reshaping help a standard compressor?](3-reshaping.md) | Yes for tables and rasters; not for prose. |
| 4 | [Do specialised models beat the usual tools?](4-specialised.md) | Scanned text yes; photos and video no. |
| 5 | [Our own text compressors on enwik8](5-text.md) | 17.8 MB: better than paq8l, behind paq8px and cmix. |
| 6 | [Working on the record archive itself](6-record-archive.md) | 0.075% smaller; nowhere near the prize. |

Reference pages: [methods](methods.md) · [glossary](glossary.md) · [every idea tried](ideas.md) ·
[rerun summary](data/rerun-summary.md).

## How the report was made

- Every chart is drawn by [`make_figures.py`](make_figures.py) from the receipts in
  [`research/large-scale/results`](../research/large-scale/results) and the files in [`data/`](data).
- [`build_scoreboard.py`](build_scoreboard.py) pairs each input with our best archive and the best standard tool.
- Each chart is written in a light and a dark version and switches with your GitHub theme.
