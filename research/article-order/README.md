# Article order: does sorting Wikipedia pages help?

> **Verdict: under 1%.** Grouping the enwik8 pages by their first category makes xz 0.65% and PPMd 0.25%
> smaller; sorting by title helps even less; a random order makes everything 0.4–0.5% larger. The decoder can undo
> the order for free (it sorts pages back by their ID).
>
> Part of [chapter 3](../../report/3-reshaping.md) of the [report](../../report/README.md).

## Question

The leading Hutter Prize entries reorder Wikipedia articles so that related pages sit together. How much does
that alone give an ordinary compressor on enwik8?

## How it works

```mermaid
flowchart LR
    E["enwik8 pages"] --> O["reorder: by title, by first category,<br/>redirects first + similarity, random"]
    O --> C["same compressors<br/>(xz, zstd, PPMd)"]
    E --> C
    C --> D["decoder sorts pages back by ID<br/>(checked by SHA-256)"]
```

[`reorder.py`](reorder.py) writes each order and checks that sorting by page ID restores enwik8 exactly
(the partial last page stays at the end). [`order_compress.py`](order_compress.py) compresses every order with
the same settings.

## Results

Full enwik8 (100,000,000 bytes). Carried over from November 18, 2026
([data](results-2026-11-18/order_results.json)); the rerun is part of [`lab-reruns.sh`](../lab-reruns.sh).

| Order | xz | zstd | PPMd |
|---|---:|---:|---:|
| Original | 24,766,840 | 25,273,903 | 21,568,890 |
| Random | 24,877,632 (+0.45%) | 25,385,713 (+0.44%) | 21,663,029 (+0.44%) |
| By title | 24,713,464 (−0.22%) | 25,217,936 (−0.22%) | 21,563,187 (−0.03%) |
| **By first category** | **24,606,200 (−0.65%)** | **25,103,825 (−0.67%)** | **21,514,114 (−0.25%)** |
| Redirects first, then similarity | 24,745,592 (−0.09%) | 25,241,301 (−0.13%) | 21,575,159 (+0.03%) |

The stronger the compressor, the less the order matters: PPMd already finds related text far apart.

## Run it

```sh
mkdir -p runs/order/work && cd runs/order
python3 ../../research/article-order/reorder.py "$CORPUS/enwik8/enwik8"
python3 ../../research/article-order/order_compress.py
```
