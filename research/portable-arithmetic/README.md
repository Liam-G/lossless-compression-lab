# Arithmetic packages that include their decoder

## Question and prior work

Does the small saving on an already compressed integer survive delivery of a working decoder? The original V15 package made the full cofactor independently recoverable. This experiment builds a new portable package from a supplied raw file, records the payload and delivery overhead, and compares the result with the separately verified V15 artifact.

## Run the experiment

```sh
python3 research/portable-arithmetic/pack.py "$Q" runs/new-q.pyz --profile informed
python3 -I -S runs/new-q.pyz runs/new-q.raw
cmp "$Q" runs/new-q.raw
python3 research/portable-arithmetic/historical.py .. runs/v15-check.json
```

## Variants and format

The encoder prices deterministic ZIP applications with a literal payload, Zstandard, XZ, and the SCL1 whole-integer scale and sparse-interval representation. XZ is considered when its prefix screen saves at least 1%. The winning package includes Python extraction code, any arithmetic and interval decoder modules, ZIP metadata and the payload. Reproduction uses Python 3.14 with the standard compression modules. The application runs with isolated mode and site packages disabled.

The historical code separately rebuilds QWX8 from the preserved QWX7 weight branch and compares the reconstructed contents using both inverse implementations. It replays the pinned complete V15 package against canonical Q. Its original top-level V14 input is absent from the workspace. The tracked V15 result therefore records a fresh branch rebuild and full decode of the retained artifact. [Original branch and package verification](historical-result.json)

## Inputs and measurement

Primary runs include canonical Q, uniform noise and transformed Wikipedia text. The informed profile admits factor 12 from the original investigation. The blind profile shortlists scales using samples. The standard-library interpreter represents the shared runtime in the delivery figures.

## Results

| Complete Q package | Bytes | Difference from 96,994,187 raw bytes |
|---|---:|---:|
| Literal application | 96,994,804 | +617 |
| Blind arithmetic selection | 96,993,979 | −208 |
| Informed arithmetic selection | 96,992,503 | −1,684 |
| Historical specialized V15 | 96,920,967 | −73,220 |

The two newly built arithmetic packages charged 2,088 bytes beyond their SCL1 payloads. The uniform control chose the literal package. [New primary measurements](../large-scale/results/by-dataset.md#cofattore-qbase256)

## Large-file benchmark

On `cofattore-Q.base256` (96,994,187 raw bytes), `portable-informed` produced 96,992,503 archive bytes. Zstandard level 3 used 96,996,424 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#cofattore-qbase256) · [All project measurements](../large-scale/results/by-experiment.md#portable-arithmetic)

## Connections

[Carry trees and sparse scales](../carry-trees/README.md) · [External reference accounting](../arithmetic-references/README.md) · [Delivering a mathematical enumerator](../whiteboard-census/README.md)
