# Text fields, BWT and move-to-front

[View this project's benchmark tables](#large-file-benchmark)

## Question and prior work

Can normalization of spelling and XML fields make Burrows–Wheeler sorting more useful on a new slice of text?

### Source files and compatibility

The text front end is ported from `lab/textfront/textfront.py`. BWT uses the retained libsais source and the move-to-front operation follows `lab/arena/view.cpp`. The new TVW1 format records the selected front end and backend for each 2 MiB block.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/text-views/codec.py encode runs/large/raw/wiki-transfer runs/wiki.tvw --profile joint
python3 research/text-views/codec.py decode runs/wiki.tvw runs/wiki.restored
cmp runs/large/raw/wiki-transfer runs/wiki.restored
```

## Variants and format

The front end can fold capitals, code frequent words, split XML bodies and store header fields by column. A dictionary and unused markers travel with each selected transformed block. The encoder checks the invertibility of a text candidate before offering it. BWT stores a primary index; move-to-front needs no extra dictionary beyond its initial byte alphabet. Direct and transformed outputs all use Zstandard 3, with literal fallback.

## Inputs and measurement

Two nonoverlapping 24 MiB windows start at byte zero and byte 67,108,864 of enwik8. Separate runs use the full Silesia NCI file and the complete Wikipedia corpora for the profiles tabulated there.

## Results

On wiki-dev the best text-only archive used 8,795,530 bytes, BWT plus move-to-front used 8,613,021 and the joint archive 8,214,112. On wiki-transfer those figures were 8,804,216, 8,637,232 and 8,231,816. Whole-file XZ extreme still produced 6,637,336 on transfer. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `wiki-transfer` (25,165,824 raw bytes), `views-joint` produced 8,231,816 archive bytes. Zstandard level 3 used 8,968,456 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#wiki-transfer) · [All project measurements](../large-scale/results/by-experiment.md#text-views)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

H0 measures byte frequencies. H1 conditions on the previous byte. Both use bits per byte of their own stream. Post H0 per raw byte accounts for changes in stream length. In the paired compressor tables, a positive percentage means preprocessing made the compressed file smaller.

### wiki-transfer · 25,165,824 raw bytes

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `views-bwt` | 25,165,956 | 5.0850 → 5.0851 | 3.8807 → 2.8011 | 5.0851 |
| `views-mtf` | 25,165,956 | 5.0850 → 2.6119 | 3.8807 → 2.3702 | 2.6119 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `views-bwt` | 9,232,082 → 8,513,896 (+7.78%) | 8,968,455 → 8,800,771 (+1.87%) | 6,743,812 → 7,360,740 (-9.15%) |
| `views-mtf` | 9,232,082 → 8,627,926 (+6.54%) | 8,968,455 → 8,662,902 (+3.41%) | 6,743,812 → 7,409,368 (-9.87%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `views-bwt` | 8,759,477 | +16,406,347 | 3.986 | 1.809 |
| `views-direct` | 9,032,653 | +16,133,171 | 1.529 | 1.393 |
| `views-joint` | 8,231,816 | +16,934,008 | 220.832 | 15.136 |
| `views-mtf` | 8,637,232 | +16,528,592 | 6.124 | 2.520 |
| `views-text` | 8,804,216 | +16,361,608 | 158.612 | 14.020 |

Same-input baseline archives (bytes) · XZ 9 extreme 6,637,336 · Zstandard 19 6,891,038 · Zstandard 3 8,968,456

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#wiki-transfer)

### enwik8 · 100,000,000 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `views-bwt` | 34,640,737 | +65,359,263 | 12.266 | 3.740 |
| `views-joint` | 32,539,733 | +67,460,267 | 427.914 | 27.341 |
| `views-mtf` | 34,159,835 | +65,840,165 | 16.425 | 4.802 |

Same-input baseline archives (bytes) · XZ 9 extreme 24,831,648 · Zstandard 19 26,944,227 · Zstandard 3 35,445,335

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#enwik8)

### enwik9 · 1,000,000,000 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `views-bwt` | 303,703,378 | +696,296,622 | 188.514 | 71.211 |
| `views-direct` | 314,928,681 | +685,071,319 | 63.886 | 21.820 |
| `views-mtf` | 299,270,871 | +700,729,129 | 152.272 | 69.987 |

Same-input baseline archives (bytes) · Zstandard 19 235,328,939 · Zstandard 3 312,109,709

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#enwik9)

### nci · 33,553,445 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `views-bwt` | 2,280,687 | +31,272,758 | 5.173 | 2.580 |
| `views-direct` | 2,864,760 | +30,688,685 | 0.831 | 0.981 |
| `views-joint` | 2,280,295 | +31,273,150 | 70.941 | 3.429 |
| `views-mtf` | 2,280,687 | +31,272,758 | 8.153 | 2.806 |
| `views-text` | 2,855,044 | +30,698,401 | 55.996 | 2.158 |

Same-input baseline archives (bytes) · XZ 9 extreme 1,449,272 · Zstandard 19 1,664,988 · Zstandard 3 2,835,400

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#nci)

### wiki-dev · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `views-bwt` | 8,728,653 | +16,437,171 | 3.093 | 1.817 |
| `views-direct` | 9,022,572 | +16,143,252 | 1.520 | 0.670 |
| `views-joint` | 8,214,112 | +16,951,712 | 188.117 | 23.217 |
| `views-mtf` | 8,613,021 | +16,552,803 | 5.837 | 2.099 |
| `views-text` | 8,795,530 | +16,370,294 | 111.136 | 11.170 |

Same-input baseline archives (bytes) · XZ 9 extreme 6,602,488 · Zstandard 19 6,873,848 · Zstandard 3 8,951,574

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#wiki-dev)

<!-- END generated project measurements -->

## Connections

Experiment 13 tests generators after BWT. [Statico](../statico/README.md) uses a grammar, and [CM3](../context-mixer/README.md) directly forecasts the original bytes.
