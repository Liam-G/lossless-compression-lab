# Integer carries across tree boundaries

[View this project's benchmark tables](#large-file-benchmark)

## Question and prior work

Does multiplying or dividing a file before splitting expose regions that the same transformation on individual leaves misses?

### Source files and compatibility

The original mixed-arity trees divide an integer and split its quotient. The hybrid Q archive in `lab/hutter/divisors/q-ibrido/ibrido.py` selects disjoint spans in 12Q. CRT1 and SCL1 are new experiments based on those two constructions.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/carry-trees/codec.py encode runs/large/raw/mapped-text runs/mapped.crt --profile joint
python3 research/carry-trees/codec.py decode runs/mapped.crt runs/mapped.restored
cmp runs/large/raw/mapped-text runs/mapped.restored
python3 research/carry-trees/sparse_scale.py encode "$Q" runs/q.scl --profile informed
python3 research/carry-trees/sparse_scale.py decode runs/q.scl runs/q-scale.restored
cmp "$Q" runs/q-scale.restored
```

## Variants and format

CRT1 uses literal, Zstandard, split and map nodes on roots up to 4 MiB. An odd multiplier is bijective modulo 2ⁿ. The power of two in a factor rotates bits, preserving those that would otherwise overflow. The inverse solves the exact carry and reverses the rotation. A map above a split carries information across its boundary. Encoder shortlist decisions cost no decoder bits. SCL1 applies a single map across the entire file and uses weighted interval scheduling over verified compressed replacements. The probe-selected `joint` profile and the `informed` profile, which adds the original lab candidate 12, are reported separately.

## Inputs and measurement

Inputs include full Q, full Neif, real numerical bytes, noise, and 24 MiB of distinct Wikipedia fragments deliberately scrambled by independent page-local arithmetic maps.

## Results

On the scrambled text the combined tree gave 9,869,511 bytes, versus 14,295,184 for splitting alone. The independent numerical input gave 13,992,442 versus 14,355,119 for arithmetic alone. The 4 MiB tree stored all of Q literally. On full Q the sparse region-only archive was 96,993,475 bytes, the whole-file joint search gave 96,991,891, and explicitly including factor 12 gave 96,990,415. The original V15 package still has the larger saving. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `cofattore-Q.base256` (96,994,187 raw bytes), `scale-informed` produced 96,990,415 archive bytes. Zstandard level 3 used 96,996,424 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#cofattore-qbase256) · [All project measurements](../large-scale/results/by-experiment.md#carry-trees)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

### cofattore-Q.base256 · 96,994,187 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `carry-arithmetic` | 96,994,223 | -36 | 6.200 | 1.479 | — / — |
| `carry-direct` | 96,994,223 | -36 | 1.547 | 0.933 | — / — |
| `carry-joint` | 96,994,223 | -36 | 43.804 | 0.543 | — / — |
| `carry-split` | 96,994,223 | -36 | 2.387 | 1.003 | — / — |
| `scale-direct` | 96,994,205 | -18 | 0.968 | 0.643 | 332,216 / 319,036 |
| `scale-informed` | 96,990,415 | +3,772 | 22.654 | 4.414 | 829,848 / 629,032 |
| `scale-joint` | 96,991,891 | +2,296 | 17.724 | 3.091 | 756,360 / 629,192 |
| `scale-regions` | 96,993,475 | +712 | 5.059 | 0.716 | 330,192 / 319,536 |
| `scale-scale` | 96,994,205 | -18 | 7.204 | 1.081 | 736,900 / 318,932 |

Same-input baseline archives (bytes) · XZ 9 extreme 96,998,528 · Zstandard 19 96,994,649 · Zstandard 3 96,996,424

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#cofattore-qbase256)

### mapped-text · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `carry-arithmetic` | 14,436,133 | +10,729,691 | 3.499 | 0.301 |
| `carry-direct` | 14,436,133 | +10,729,691 | 1.006 | 0.417 |
| `carry-joint` | 9,869,511 | +15,296,313 | 30.406 | 0.943 |
| `carry-split` | 14,295,184 | +10,870,640 | 5.485 | 0.552 |

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#mapped-text)

### neif-archive9 · 89,346,392 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `carry-arithmetic` | 89,346,426 | -34 | 4.039 | 0.923 | — / — |
| `carry-direct` | 89,346,426 | -34 | 0.700 | 0.754 | — / — |
| `carry-joint` | 89,346,426 | -34 | 33.529 | 1.000 | — / — |
| `carry-split` | 89,346,426 | -34 | 2.205 | 0.734 | — / — |
| `scale-direct` | 89,346,410 | -18 | 1.709 | 1.372 | 309,936 / 296,692 |
| `scale-joint` | 89,346,307 | +85 | 17.144 | 0.714 | 685,272 / 296,568 |
| `scale-regions` | 89,346,307 | +85 | 5.242 | 1.037 | 306,308 / 296,752 |

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#neif-archive9)

### numerical · 25,696,748 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `carry-arithmetic` | 14,355,119 | +11,341,629 | 2.797 | 0.464 |
| `carry-direct` | 15,175,129 | +10,521,619 | 0.955 | 0.465 |
| `carry-joint` | 13,992,442 | +11,704,306 | 42.440 | 0.788 |
| `carry-split` | 15,117,918 | +10,578,830 | 5.278 | 0.415 |

Same-input baseline archives (bytes) · XZ 9 extreme 11,662,476 · Zstandard 19 13,213,336 · Zstandard 3 15,163,683

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#numerical)

### uniform · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `carry-arithmetic` | 25,165,842 | -18 | 1.716 | 0.542 | — / — |
| `carry-direct` | 25,165,842 | -18 | 0.405 | 0.503 | — / — |
| `carry-joint` | 25,165,842 | -18 | 9.305 | 0.213 | — / — |
| `carry-split` | 25,165,842 | -18 | 0.565 | 0.207 | — / — |
| `scale-joint` | 25,165,842 | -18 | 8.231 | 0.928 | 214,524 / 108,528 |

Same-input baseline archives (bytes) · XZ 9 extreme 25,167,136 · Zstandard 19 25,166,414 · Zstandard 3 25,166,414

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#uniform)

<!-- END generated project measurements -->

## Connections

Compare with [whiteboard trees](../whiteboard-trees/README.md), [whole-integer formulas](../integer-formulas/README.md) and [arithmetic reference patches](../arithmetic-references/README.md).
