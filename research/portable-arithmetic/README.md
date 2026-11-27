# Arithmetic packages that include their decoder

[View this project's benchmark tables](#large-file-benchmark)

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

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

### cofattore-Q.base256 · 96,994,187 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `portable-informed` | 96,992,503 | +1,684 | 51.545 | 8.723 | 923,824 / 608,672 |
| `portable-joint` | 96,993,979 | +208 | 35.083 | 9.658 | 848,756 / 608,988 |
| `portable-literal` | 96,994,804 | -617 | 1.750 | 0.667 | 221,988 / 108,568 |
| `portable-standard` | 96,994,804 | -617 | 3.940 | 1.540 | 414,172 / 108,568 |

Same-input baseline archives (bytes) · XZ 9 extreme 96,998,528 · Zstandard 19 96,994,649 · Zstandard 3 96,996,424

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#cofattore-qbase256)

### mapped-text · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `portable-joint` | 11,823,400 | +13,342,424 | 409.590 | 4.131 | 333,856 / 84,068 |
| `portable-literal` | 25,166,441 | -617 | 1.504 | 0.915 | 83,832 / 38,696 |
| `portable-standard` | 11,823,400 | +13,342,424 | 47.171 | 2.593 | 191,800 / 82,968 |

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#mapped-text)

### uniform · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `portable-informed` | 25,166,441 | -617 | 12.871 | 0.618 | 285,848 / 38,704 |
| `portable-standard` | 25,166,441 | -617 | 2.349 | 0.997 | 133,768 / 38,628 |

Same-input baseline archives (bytes) · XZ 9 extreme 25,167,136 · Zstandard 19 25,166,414 · Zstandard 3 25,166,414

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#uniform)

<!-- END generated project measurements -->

## Connections

[Carry trees and sparse scales](../carry-trees/README.md) · [External reference accounting](../arithmetic-references/README.md) · [Delivering a mathematical enumerator](../whiteboard-census/README.md)
