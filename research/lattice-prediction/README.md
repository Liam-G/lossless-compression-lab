# Local integer grids and bit-plane residuals

[View this project's benchmark tables](#large-file-benchmark)

## Question and prior work

Can a file disclose its sample width and lag without an image or scientific-format parser? Do those predictors help once a general entropy coder sees the separated bit planes?

A second experiment studies variable-width records. On NOAA weather observations, neighboring values in the same field share enough structure to cut Zstandard size by over 40% in two separate years. [Ragged rows, CSV fields and prefix coding](ragged-rows.md)

### Source files and compatibility

The historical `lab/shape/nested.py` measured conditional entropy from rows, byte lanes and planes of the original data. This new encoder turns the same idea into an actual inverse and compares the cost of its complete records.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/lattice-prediction/codec.py encode runs/large/raw/numerical runs/grid.ltp --profile joint-xz
python3 research/lattice-prediction/codec.py decode runs/grid.ltp runs/grid.restored
cmp runs/large/raw/numerical runs/grid.restored
```

## Variants and format

Each 1 MiB block tries 1-, 2- and 4-byte unsigned little-endian samples. Dispersed points shortlist lags; modular first differences, XOR, second differences, or a mixed two-axis derivative predict the current value. ZigZag maps signed differences back to fixed-width integers. Whole bytes, byte lanes and bit planes share the same backend. LTP1 uses Zstandard. LTX1 reprices the three best fast candidates and the unmodified block with XZ preset 6. The original length, per-block width, lag, predictor, layout, payload and tail are all recoverable.

## Inputs and measurement

The numerical file concatenates complete Silesia mr, x-ray and sao in that order. Other files include textual Silesia members, binary software, disjoint Wikipedia text, matched noise and derived distance matrices. The 1 MiB block boundaries cross the two numerical member boundaries.

## Results

On 25,696,748 numerical bytes, layout alone gave 13,018,122, prediction alone 13,025,639 and their joint Zstd-3 representation 11,654,765. Repricing with Zstd-19 gave 11,006,699. The matched blocked XZ control was 11,846,741 and the joint XZ archive 10,421,725. Whole-file XZ extreme gave 11,662,476. The gain disappeared on the held-out Wikipedia text. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `numerical` (25,696,748 raw bytes), `lattice-joint-xz` produced 10,421,725 archive bytes. Zstandard level 3 used 15,163,683 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#numerical) · [All project measurements](../large-scale/results/by-experiment.md#lattice-prediction)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

H0 measures byte frequencies. H1 conditions on the previous byte. Both use bits per byte of their own stream. Post H0 per raw byte accounts for changes in stream length. In the paired compressor tables, a positive percentage means preprocessing made the compressed file smaller.

### numerical · 25,696,748 raw bytes

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `lattice-joint` | 25,696,985 | 6.3494 → 4.9333 | 5.5271 → 3.7053 | 4.9333 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `lattice-joint` | 15,063,439 → 11,486,297 (+23.75%) | 15,163,679 → 11,635,203 (+23.27%) | 11,665,916 → 10,449,384 (+10.43%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `lattice-direct` | 15,227,864 | +10,468,884 | 0.558 | 0.326 |
| `lattice-direct-xz` | 11,846,741 | +13,850,007 | 36.848 | 5.020 |
| `lattice-direct19` | 13,601,994 | +12,094,754 | 23.956 | 0.754 |
| `lattice-joint` | 11,654,765 | +14,041,983 | 33.323 | 0.978 |
| `lattice-joint-xz` | 10,421,725 | +15,275,023 | 241.002 | 6.900 |
| `lattice-joint19` | 11,006,699 | +14,690,049 | 169.782 | 4.740 |
| `lattice-layout` | 13,018,122 | +12,678,626 | 3.755 | 1.258 |
| `lattice-predict` | 13,025,639 | +12,671,109 | 7.935 | 0.431 |

Same-input baseline archives (bytes) · XZ 9 extreme 11,662,476 · Zstandard 19 13,213,336 · Zstandard 3 15,163,683

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#numerical)

<details>
<summary>covertype-prefix · 25,165,824 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `lattice-rows-field-positions` | 25,215,468 | 2.2843 → 2.3029 | 1.3298 → 1.0673 | 2.3075 |
| `lattice-rows-field-prefix` | 26,256,422 | 2.2843 → 2.5326 | 1.3298 → 1.2712 | 2.6424 |
| `lattice-rows-fields` | 25,169,388 | 2.2843 → 2.2866 | 1.3298 → 1.3302 | 2.2869 |
| `lattice-rows-joint` | 25,166,796 | 2.2843 → 1.3312 | 1.3298 → 0.9613 | 1.3312 |
| `lattice-rows-prefix` | 27,491,616 | 2.2843 → 2.6163 | 1.3298 → 1.3132 | 2.8581 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `lattice-rows-field-positions` | 3,778,786 → 2,410,868 (+36.20%) | 3,997,073 → 2,493,345 (+37.62%) | 2,801,076 → 1,816,048 (+35.17%) |
| `lattice-rows-field-prefix` | 3,778,786 → 3,198,897 (+15.35%) | 3,997,073 → 3,365,027 (+15.81%) | 2,801,076 → 2,283,648 (+18.47%) |
| `lattice-rows-fields` | 3,778,786 → 3,279,530 (+13.21%) | 3,997,073 → 3,372,812 (+15.62%) | 2,801,076 → 2,198,712 (+21.50%) |
| `lattice-rows-joint` | 3,778,786 → 3,312,836 (+12.33%) | 3,997,073 → 3,422,678 (+14.37%) | 2,801,076 → 2,742,460 (+2.09%) |
| `lattice-rows-prefix` | 3,778,786 → 4,039,129 (-6.89%) | 3,997,073 → 4,185,009 (-4.70%) | 2,801,076 → 2,966,092 (-5.89%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-rows-field-positions` | 2,499,177 | +22,666,647 | 0.525 | 0.420 | 62,632 / 36,820 |
| `lattice-rows-field-prefix` | 3,360,912 | +21,804,912 | 0.561 | 0.413 | 65,344 / 36,704 |
| `lattice-rows-fields` | 3,371,995 | +21,793,829 | 0.698 | 0.492 | 64,196 / 36,568 |
| `lattice-rows-joint` | 3,427,252 | +21,738,572 | 0.687 | 0.580 | 67,588 / 40,960 |
| `lattice-rows-prefix` | 4,181,076 | +20,984,748 | 0.951 | 0.663 | 68,184 / 36,572 |

Same-input baseline archives (bytes) · Zstandard 3 3,997,074

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#covertype-prefix)

</details>

<details>
<summary>mesa-update · 67,133,440 raw bytes</summary>

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-joint19` | 18,718,222 | +48,415,218 | 350.731 | 0.890 | 79,436 / 43,940 |

Same-input baseline archives (bytes) · XZ 9 extreme 16,198,184 · Zstandard 19 17,697,935 · Zstandard 3 21,668,962

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#mesa-update)

</details>

<details>
<summary>mozilla · 51,220,480 raw bytes</summary>

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-direct` | 18,547,895 | +32,672,585 | 0.457 | 0.309 | — / — |
| `lattice-direct-xz` | 14,330,877 | +36,889,603 | 34.121 | 1.663 | 70,672 / 44,756 |
| `lattice-direct19` | 15,972,267 | +35,248,213 | 35.539 | 0.773 | 58,352 / 39,844 |
| `lattice-joint` | 18,528,219 | +32,692,261 | 142.724 | 0.439 | — / — |
| `lattice-joint-xz` | 14,328,741 | +36,891,739 | 504.666 | 4.425 | 89,644 / 44,800 |
| `lattice-joint19` | 15,949,364 | +35,271,116 | 283.573 | 0.715 | 79,376 / 39,964 |
| `lattice-layout` | 18,528,219 | +32,692,261 | 6.034 | 0.320 | — / — |
| `lattice-predict` | 18,547,895 | +32,672,585 | 13.998 | 0.464 | — / — |

Same-input baseline archives (bytes) · XZ 9 extreme 13,376,240 · Zstandard 19 15,071,672 · Zstandard 3 18,281,292

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#mozilla)

</details>

<details>
<summary>nci · 33,553,445 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `lattice-rows-above` | 33,554,761 | 2.4293 → 1.7313 | 1.9466 → 1.0145 | 1.7314 |
| `lattice-rows-columns` | 33,554,761 | 2.4293 → 2.4775 | 1.9466 → 0.6467 | 2.4776 |
| `lattice-rows-delta` | 33,554,761 | 2.4293 → 1.2887 | 1.9466 → 0.8982 | 1.2888 |
| `lattice-rows-field-positions` | 33,619,633 | 2.4293 → 2.4463 | 1.9466 → 1.7480 | 2.4511 |
| `lattice-rows-field-prefix` | 31,636,805 | 2.4293 → 2.6398 | 1.9466 → 1.9028 | 2.4890 |
| `lattice-rows-fields` | 33,558,193 | 2.4293 → 2.4309 | 1.9466 → 1.9466 | 2.4313 |
| `lattice-rows-framed` | 33,554,761 | 2.4293 → 2.4775 | 1.9466 → 1.8443 | 2.4776 |
| `lattice-rows-joint` | 33,554,761 | 2.4293 → 1.2887 | 1.9466 → 0.7681 | 1.2888 |
| `lattice-rows-prefix` | 31,633,221 | 2.4293 → 2.6393 | 1.9466 → 1.9022 | 2.4882 |
| `lattice-rows-route-select` | 33,554,761 | 2.4293 → 2.5964 | 1.9466 → 0.6633 | 2.5965 |
| `lattice-rows-select` | 33,554,761 | 2.4293 → 2.5964 | 1.9466 → 0.6633 | 2.5965 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `lattice-rows-above` | 3,199,449 → 3,558,372 (-11.22%) | 2,835,396 → 3,218,569 (-13.51%) | 1,779,272 → 2,070,980 (-16.39%) |
| `lattice-rows-columns` | 3,199,449 → 2,363,037 (+26.14%) | 2,835,396 → 2,489,621 (+12.19%) | 1,779,272 → 1,872,004 (-5.21%) |
| `lattice-rows-delta` | 3,199,449 → 3,513,161 (-9.81%) | 2,835,396 → 3,259,904 (-14.97%) | 1,779,272 → 2,167,976 (-21.85%) |
| `lattice-rows-field-positions` | 3,199,449 → 2,944,428 (+7.97%) | 2,835,396 → 3,183,691 (-12.28%) | 1,779,272 → 2,243,240 (-26.08%) |
| `lattice-rows-field-prefix` | 3,199,449 → 3,141,871 (+1.80%) | 2,835,396 → 2,943,388 (-3.81%) | 1,779,272 → 1,770,816 (+0.48%) |
| `lattice-rows-fields` | 3,199,449 → 3,201,668 (-0.07%) | 2,835,396 → 2,836,967 (-0.06%) | 1,779,272 → 1,780,856 (-0.09%) |
| `lattice-rows-framed` | 3,199,449 → 3,254,607 (-1.72%) | 2,835,396 → 2,897,093 (-2.18%) | 1,779,272 → 1,811,796 (-1.83%) |
| `lattice-rows-joint` | 3,199,449 → 2,710,424 (+15.28%) | 2,835,396 → 2,761,194 (+2.62%) | 1,779,272 → 2,126,876 (-19.54%) |
| `lattice-rows-prefix` | 3,199,449 → 3,141,513 (+1.81%) | 2,835,396 → 2,942,762 (-3.79%) | 1,779,272 → 1,770,432 (+0.50%) |
| `lattice-rows-route-select` | 3,199,449 → 2,375,281 (+25.76%) | 2,835,396 → 2,483,811 (+12.40%) | 1,779,272 → 1,866,432 (-4.90%) |
| `lattice-rows-select` | 3,199,449 → 2,375,281 (+25.76%) | 2,835,396 → 2,483,811 (+12.40%) | 1,779,272 → 1,866,432 (-4.90%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-direct` | 2,897,140 | +30,656,305 | 0.382 | 0.333 | — / — |
| `lattice-joint` | 2,897,140 | +30,656,305 | 60.025 | 0.281 | — / — |
| `lattice-layout` | 2,897,140 | +30,656,305 | 4.852 | 0.341 | — / — |
| `lattice-predict` | 2,897,140 | +30,656,305 | 5.588 | 0.273 | — / — |
| `lattice-rows-above` | 3,210,541 | +30,342,904 | 5.134 | 4.989 | 73,636 / 38,756 |
| `lattice-rows-columns` | 2,499,589 | +31,053,856 | 1.590 | 0.869 | 73,928 / 40,604 |
| `lattice-rows-delta` | 3,252,940 | +30,300,505 | 1.820 | 1.893 | 76,472 / 42,360 |
| `lattice-rows-field-positions` | 3,186,434 | +30,367,011 | 1.790 | 0.723 | 73,200 / 36,560 |
| `lattice-rows-field-prefix` | 2,939,827 | +30,613,618 | 0.537 | 0.527 | 72,048 / 39,124 |
| `lattice-rows-fields` | 2,834,997 | +30,718,448 | 0.787 | 0.565 | 73,452 / 38,352 |
| `lattice-rows-framed` | 2,894,848 | +30,658,597 | 1.105 | 0.787 | 72,644 / 38,104 |
| `lattice-rows-joint` | 2,763,518 | +30,789,927 | 1.343 | 1.611 | 75,852 / 42,656 |
| `lattice-rows-prefix` | 2,939,148 | +30,614,297 | 0.551 | 0.396 | 72,076 / 36,896 |
| `lattice-rows-route-select` | 2,493,007 | +31,060,438 | 9.648 | 1.492 | 78,160 / 40,752 |
| `lattice-rows-select` | 2,493,007 | +31,060,438 | 6.897 | 1.325 | 75,084 / 40,636 |

Same-input baseline archives (bytes) · XZ 9 extreme 1,449,272 · Zstandard 19 1,664,988 · Zstandard 3 2,835,400

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#nci)

</details>

<details>
<summary>nci-row-shuffled · 33,553,445 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `lattice-rows-columns` | 33,554,761 | 2.4293 → 2.4775 | 2.3190 → 2.1755 | 2.4776 |
| `lattice-rows-delta` | 33,554,761 | 2.4293 → 3.9131 | 2.3190 → 3.6970 | 3.9132 |
| `lattice-rows-field-positions` | 33,619,633 | 2.4293 → 2.4463 | 2.3190 → 2.3469 | 2.4511 |
| `lattice-rows-field-prefix` | 33,942,978 | 2.4293 → 2.5895 | 2.3190 → 2.3101 | 2.6195 |
| `lattice-rows-fields` | 33,558,193 | 2.4293 → 2.4309 | 2.3190 → 2.3189 | 2.4313 |
| `lattice-rows-framed` | 33,554,761 | 2.4293 → 2.4775 | 2.3190 → 2.1714 | 2.4776 |
| `lattice-rows-joint` | 33,554,761 | 2.4293 → 3.9131 | 2.3190 → 2.6379 | 3.9132 |
| `lattice-rows-prefix` | 33,939,394 | 2.4293 → 2.5891 | 2.3190 → 2.3095 | 2.6189 |
| `lattice-rows-route-select` | 33,554,761 | 2.4293 → 2.4775 | 2.3190 → 2.1755 | 2.4776 |
| `lattice-rows-select` | 33,554,761 | 2.4293 → 2.4775 | 2.3190 → 2.1755 | 2.4776 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `lattice-rows-columns` | 12,395,907 → 11,476,737 (+7.42%) | 12,578,509 → 11,833,316 (+5.92%) | 10,671,000 → 9,958,468 (+6.68%) |
| `lattice-rows-delta` | 12,395,907 → 18,304,913 (-47.67%) | 12,578,509 → 18,077,269 (-43.72%) | 10,671,000 → 16,246,772 (-52.25%) |
| `lattice-rows-field-positions` | 12,395,907 → 12,374,847 (+0.17%) | 12,578,509 → 12,691,175 (-0.90%) | 10,671,000 → 10,804,532 (-1.25%) |
| `lattice-rows-field-prefix` | 12,395,907 → 12,627,602 (-1.87%) | 12,578,509 → 12,812,624 (-1.86%) | 10,671,000 → 10,796,956 (-1.18%) |
| `lattice-rows-fields` | 12,395,907 → 12,398,506 (-0.02%) | 12,578,509 → 12,579,574 (-0.01%) | 10,671,000 → 10,672,884 (-0.02%) |
| `lattice-rows-framed` | 12,395,907 → 11,731,819 (+5.36%) | 12,578,509 → 11,915,614 (+5.27%) | 10,671,000 → 10,081,648 (+5.52%) |
| `lattice-rows-joint` | 12,395,907 → 13,695,892 (-10.49%) | 12,578,509 → 13,578,836 (-7.95%) | 10,671,000 → 11,270,408 (-5.62%) |
| `lattice-rows-prefix` | 12,395,907 → 12,627,056 (-1.86%) | 12,578,509 → 12,811,858 (-1.86%) | 10,671,000 → 10,795,476 (-1.17%) |
| `lattice-rows-route-select` | 12,395,907 → 11,476,737 (+7.42%) | 12,578,509 → 11,833,316 (+5.92%) | 10,671,000 → 9,958,468 (+6.68%) |
| `lattice-rows-select` | 12,395,907 → 11,476,737 (+7.42%) | 12,578,509 → 11,833,316 (+5.92%) | 10,671,000 → 9,958,468 (+6.68%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-rows-columns` | 11,837,029 | +21,716,416 | 1.897 | 1.077 | 95,144 / 42,040 |
| `lattice-rows-delta` | 18,077,240 | +15,476,205 | 2.864 | 1.626 | 107,112 / 42,604 |
| `lattice-rows-field-positions` | 12,695,852 | +20,857,593 | 0.615 | 0.343 | 93,520 / 38,712 |
| `lattice-rows-field-prefix` | 12,815,904 | +20,737,541 | 0.822 | 0.583 | 95,064 / 36,728 |
| `lattice-rows-fields` | 12,584,223 | +20,969,222 | 0.674 | 0.406 | 92,836 / 38,748 |
| `lattice-rows-framed` | 11,919,156 | +21,634,289 | 1.308 | 0.869 | 91,084 / 37,764 |
| `lattice-rows-joint` | 13,576,147 | +19,977,298 | 2.585 | 1.769 | 101,184 / 42,400 |
| `lattice-rows-prefix` | 12,813,712 | +20,739,733 | 0.805 | 0.491 | 94,980 / 36,736 |
| `lattice-rows-route-select` | 11,837,029 | +21,716,416 | 15.192 | 1.596 | 97,768 / 42,604 |
| `lattice-rows-select` | 11,837,029 | +21,716,416 | 11.072 | 1.390 | 97,368 / 42,320 |

Same-input baseline archives (bytes) · Zstandard 3 12,578,513

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#nci-row-shuffled)

</details>

<details>
<summary>noaa-1990-prefix · 25,165,824 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `lattice-rows-above` | 25,166,796 | 3.9764 → 2.1622 | 2.6846 → 1.4320 | 2.1623 |
| `lattice-rows-columns` | 25,166,796 | 3.9764 → 4.0526 | 2.6846 → 1.0043 | 4.0528 |
| `lattice-rows-delta` | 25,166,796 | 3.9764 → 1.5805 | 2.6846 → 1.0964 | 1.5805 |
| `lattice-rows-field-positions` | 25,215,468 | 3.9764 → 3.9918 | 2.6846 → 0.9572 | 3.9997 |
| `lattice-rows-field-prefix` | 15,572,584 | 3.9764 → 3.7762 | 2.6846 → 1.9335 | 2.3367 |
| `lattice-rows-fields` | 25,169,388 | 3.9764 → 3.9783 | 2.6846 → 2.6957 | 3.9789 |
| `lattice-rows-framed` | 25,166,796 | 3.9764 → 4.0526 | 2.6846 → 2.7191 | 4.0528 |
| `lattice-rows-joint` | 25,166,796 | 3.9764 → 1.5805 | 2.6846 → 1.0309 | 1.5805 |
| `lattice-rows-literal` | 25,166,316 | 3.9764 → 3.9767 | 2.6846 → 2.6847 | 3.9767 |
| `lattice-rows-positions` | 25,172,460 | 3.9764 → 3.9796 | 2.6846 → 3.0985 | 3.9806 |
| `lattice-rows-prefix` | 30,802,601 | 3.9764 → 3.9579 | 2.6846 → 2.2792 | 4.8444 |
| `lattice-rows-route-select` | 25,176,534 | 3.9764 → 3.9859 | 2.6846 → 2.6750 | 3.9876 |
| `lattice-rows-select` | 25,166,786 | 3.9764 → 4.1541 | 2.6846 → 1.1110 | 4.1543 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `lattice-rows-above` | 3,222,875 → 3,242,863 (-0.62%) | 3,541,939 → 3,343,075 (+5.61%) | 1,816,516 → 1,956,820 (-7.72%) |
| `lattice-rows-columns` | 3,222,875 → 2,876,387 (+10.75%) | 3,541,939 → 3,221,769 (+9.04%) | 1,816,516 → 2,273,628 (-25.16%) |
| `lattice-rows-delta` | 3,222,875 → 3,572,013 (-10.83%) | 3,541,939 → 3,835,972 (-8.30%) | 1,816,516 → 2,262,664 (-24.56%) |
| `lattice-rows-field-positions` | 3,222,875 → 2,001,710 (+37.89%) | 3,541,939 → 2,307,035 (+34.87%) | 1,816,516 → 1,276,732 (+29.72%) |
| `lattice-rows-field-prefix` | 3,222,875 → 1,705,482 (+47.08%) | 3,541,939 → 1,870,761 (+47.18%) | 1,816,516 → 994,236 (+45.27%) |
| `lattice-rows-fields` | 3,222,875 → 1,913,577 (+40.63%) | 3,541,939 → 2,086,007 (+41.11%) | 1,816,516 → 957,348 (+47.30%) |
| `lattice-rows-framed` | 3,222,875 → 3,456,834 (-7.26%) | 3,541,939 → 3,744,492 (-5.72%) | 1,816,516 → 1,992,436 (-9.68%) |
| `lattice-rows-joint` | 3,222,875 → 3,209,091 (+0.43%) | 3,541,939 → 3,402,507 (+3.94%) | 1,816,516 → 2,564,352 (-41.17%) |
| `lattice-rows-literal` | 3,222,875 → 3,223,895 (-0.03%) | 3,541,939 → 3,542,684 (-0.02%) | 1,816,516 → 1,818,896 (-0.13%) |
| `lattice-rows-positions` | 3,222,875 → 2,655,397 (+17.61%) | 3,541,939 → 3,164,406 (+10.66%) | 1,816,516 → 1,691,612 (+6.88%) |
| `lattice-rows-prefix` | 3,222,875 → 3,354,183 (-4.07%) | 3,541,939 → 3,784,147 (-6.84%) | 1,816,516 → 1,882,168 (-3.61%) |
| `lattice-rows-route-select` | 3,222,875 → 1,852,984 (+42.51%) | 3,541,939 → 2,032,120 (+42.63%) | 1,816,516 → 1,043,020 (+42.58%) |
| `lattice-rows-select` | 3,222,875 → 2,891,968 (+10.27%) | 3,541,939 → 3,216,603 (+9.19%) | 1,816,516 → 2,261,252 (-24.48%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-rows-above` | 3,342,275 | +21,823,549 | 5.589 | 5.536 | 65,672 / 38,320 |
| `lattice-rows-columns` | 3,234,817 | +21,931,007 | 1.382 | 1.032 | 67,784 / 42,824 |
| `lattice-rows-delta` | 3,834,129 | +21,331,695 | 1.403 | 1.248 | 67,668 / 40,188 |
| `lattice-rows-field-positions` | 2,296,741 | +22,869,083 | 1.312 | 0.805 | 63,520 / 36,156 |
| `lattice-rows-field-prefix` | 1,851,287 | +23,314,537 | 1.679 | 0.685 | 54,792 / 36,668 |
| `lattice-rows-fields` | 2,066,584 | +23,099,240 | 1.139 | 0.974 | 64,176 / 36,232 |
| `lattice-rows-framed` | 3,746,780 | +21,419,044 | 1.027 | 0.832 | 67,296 / 37,632 |
| `lattice-rows-joint` | 3,407,235 | +21,758,589 | 1.110 | 1.031 | 67,044 / 40,992 |
| `lattice-rows-literal` | 3,546,099 | +21,619,725 | 0.428 | 0.308 | 67,796 / 38,080 |
| `lattice-rows-positions` | 3,163,742 | +22,002,082 | 1.115 | 0.903 | 65,288 / 36,488 |
| `lattice-rows-prefix` | 3,786,850 | +21,378,974 | 1.465 | 0.798 | 72,164 / 36,764 |
| `lattice-rows-route-select` | 2,014,421 | +23,151,403 | 9.414 | 0.997 | 67,736 / 39,580 |
| `lattice-rows-select` | 3,230,095 | +21,935,729 | 7.515 | 1.355 | 67,728 / 40,380 |

Same-input baseline archives (bytes) · Zstandard 3 3,541,940

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#noaa-1990-prefix)

</details>

<details>
<summary>noaa-2020-prefix · 25,165,824 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `lattice-rows-above` | 25,166,796 | 3.9485 → 2.1309 | 2.8067 → 1.4288 | 2.1309 |
| `lattice-rows-columns` | 25,166,796 | 3.9485 → 4.0258 | 2.8067 → 1.0384 | 4.0260 |
| `lattice-rows-delta` | 25,166,796 | 3.9485 → 1.6280 | 2.8067 → 1.1176 | 1.6281 |
| `lattice-rows-field-positions` | 25,215,468 | 3.9485 → 3.9639 | 2.8067 → 0.9553 | 3.9717 |
| `lattice-rows-field-prefix` | 15,393,657 | 3.9485 → 3.8387 | 2.8067 → 2.0128 | 2.3481 |
| `lattice-rows-fields` | 25,169,388 | 3.9485 → 3.9504 | 2.8067 → 2.8159 | 3.9510 |
| `lattice-rows-framed` | 25,166,796 | 3.9485 → 4.0258 | 2.8067 → 2.8370 | 4.0260 |
| `lattice-rows-joint` | 25,166,796 | 3.9485 → 1.6280 | 2.8067 → 1.0679 | 1.6281 |
| `lattice-rows-literal` | 25,166,316 | 3.9485 → 3.9488 | 2.8067 → 2.8068 | 3.9489 |
| `lattice-rows-positions` | 25,172,460 | 3.9485 → 3.9516 | 2.8067 → 3.2197 | 3.9527 |
| `lattice-rows-prefix` | 30,783,066 | 3.9485 → 3.9139 | 2.8067 → 2.3761 | 4.7875 |
| `lattice-rows-route-select` | 25,172,268 | 3.9485 → 3.9516 | 2.8067 → 2.8413 | 3.9526 |
| `lattice-rows-select` | 25,166,796 | 3.9485 → 4.0258 | 2.8067 → 1.0384 | 4.0260 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `lattice-rows-above` | 3,271,833 → 3,360,252 (-2.70%) | 3,552,108 → 3,517,969 (+0.96%) | 1,854,284 → 2,033,280 (-9.65%) |
| `lattice-rows-columns` | 3,271,833 → 2,943,377 (+10.04%) | 3,552,108 → 3,292,962 (+7.30%) | 1,854,284 → 2,344,304 (-26.43%) |
| `lattice-rows-delta` | 3,271,833 → 3,618,964 (-10.61%) | 3,552,108 → 3,888,816 (-9.48%) | 1,854,284 → 2,252,304 (-21.46%) |
| `lattice-rows-field-positions` | 3,271,833 → 2,081,857 (+36.37%) | 3,552,108 → 2,364,895 (+33.42%) | 1,854,284 → 1,466,456 (+20.92%) |
| `lattice-rows-field-prefix` | 3,271,833 → 1,767,719 (+45.97%) | 3,552,108 → 2,012,489 (+43.34%) | 1,854,284 → 1,095,256 (+40.93%) |
| `lattice-rows-fields` | 3,271,833 → 1,917,471 (+41.39%) | 3,552,108 → 2,100,930 (+40.85%) | 1,854,284 → 1,065,376 (+42.55%) |
| `lattice-rows-framed` | 3,271,833 → 3,477,930 (-6.30%) | 3,552,108 → 3,741,542 (-5.33%) | 1,854,284 → 2,017,200 (-8.79%) |
| `lattice-rows-joint` | 3,271,833 → 3,272,224 (-0.01%) | 3,552,108 → 3,474,417 (+2.19%) | 1,854,284 → 2,643,928 (-42.58%) |
| `lattice-rows-literal` | 3,271,833 → 3,272,923 (-0.03%) | 3,552,108 → 3,552,823 (-0.02%) | 1,854,284 → 1,855,884 (-0.09%) |
| `lattice-rows-positions` | 3,271,833 → 2,800,785 (+14.40%) | 3,552,108 → 3,322,140 (+6.47%) | 1,854,284 → 1,852,440 (+0.10%) |
| `lattice-rows-prefix` | 3,271,833 → 3,393,947 (-3.73%) | 3,552,108 → 3,763,027 (-5.94%) | 1,854,284 → 1,917,724 (-3.42%) |
| `lattice-rows-route-select` | 3,271,833 → 1,909,412 (+41.64%) | 3,552,108 → 2,085,342 (+41.29%) | 1,854,284 → 1,098,844 (+40.74%) |
| `lattice-rows-select` | 3,271,833 → 2,943,377 (+10.04%) | 3,552,108 → 3,292,962 (+7.30%) | 1,854,284 → 2,344,304 (-26.43%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-rows-above` | 3,519,194 | +21,646,630 | 3.526 | 4.715 | 65,932 / 38,548 |
| `lattice-rows-columns` | 3,302,573 | +21,863,251 | 1.455 | 1.191 | 66,312 / 40,596 |
| `lattice-rows-delta` | 3,887,200 | +21,278,624 | 1.185 | 1.112 | 71,004 / 41,116 |
| `lattice-rows-field-positions` | 2,354,265 | +22,811,559 | 1.218 | 0.568 | 63,632 / 36,628 |
| `lattice-rows-field-prefix` | 2,002,982 | +23,162,842 | 1.001 | 1.219 | 53,796 / 36,604 |
| `lattice-rows-fields` | 2,077,403 | +23,088,421 | 1.267 | 0.751 | 62,996 / 36,180 |
| `lattice-rows-framed` | 3,741,661 | +21,424,163 | 1.073 | 0.713 | 67,100 / 38,132 |
| `lattice-rows-joint` | 3,478,146 | +21,687,678 | 1.035 | 1.203 | 68,236 / 40,932 |
| `lattice-rows-literal` | 3,554,623 | +21,611,201 | 0.422 | 0.301 | 67,944 / 36,096 |
| `lattice-rows-positions` | 3,318,696 | +21,847,128 | 1.059 | 0.908 | 67,568 / 38,372 |
| `lattice-rows-prefix` | 3,767,003 | +21,398,821 | 1.678 | 1.024 | 72,196 / 36,924 |
| `lattice-rows-route-select` | 2,062,346 | +23,103,478 | 7.225 | 0.636 | 65,384 / 36,584 |
| `lattice-rows-select` | 3,302,573 | +21,863,251 | 7.654 | 1.233 | 67,704 / 41,008 |

Same-input baseline archives (bytes) · Zstandard 3 3,552,109

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#noaa-2020-prefix)

</details>

<details>
<summary>numpy-update · 53,800,960 raw bytes</summary>

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `lattice-joint19` | 10,519,150 | +43,281,810 | 399.612 | 0.985 |

Same-input baseline archives (bytes) · XZ 9 extreme 8,272,288 · Zstandard 19 9,104,011 · Zstandard 3 11,502,762

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#numpy-update)

</details>

<details>
<summary>place-distances · 21,155,400 raw bytes</summary>

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-joint19` | 13,100,968 | +8,054,432 | 121.806 | 1.341 | 83,368 / 46,016 |

Same-input baseline archives (bytes) · XZ 9 extreme 16,711,344 · Zstandard 19 19,356,133 · Zstandard 3 20,188,613

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#place-distances)

</details>

<details>
<summary>samba · 21,606,400 raw bytes</summary>

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `lattice-direct` | 5,192,593 | +16,413,807 | 0.496 | 0.311 |
| `lattice-direct-xz` | 4,239,761 | +17,366,639 | 30.868 | 1.533 |
| `lattice-direct19` | 4,365,638 | +17,240,762 | 46.114 | 2.155 |
| `lattice-joint` | 5,153,877 | +16,452,523 | 58.585 | 0.562 |
| `lattice-joint-xz` | 4,239,761 | +17,366,639 | 148.986 | 0.913 |
| `lattice-joint19` | 4,365,148 | +17,241,252 | 263.960 | 1.046 |
| `lattice-layout` | 5,153,877 | +16,452,523 | 5.900 | 0.463 |
| `lattice-predict` | 5,192,593 | +16,413,807 | 7.866 | 0.373 |

Same-input baseline archives (bytes) · XZ 9 extreme 3,739,524 · Zstandard 19 3,894,675 · Zstandard 3 4,957,768

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#samba)

</details>

<details>
<summary>uniform · 25,165,824 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `lattice-rows-joint` | 25,312,096 | 8.0000 → 7.9964 | 7.9981 → 7.9819 | 8.0429 |
| `lattice-rows-route-select` | 25,166,316 | 8.0000 → 8.0000 | 7.9981 → 7.9981 | 8.0001 |
| `lattice-rows-select` | 25,166,316 | 8.0000 → 8.0000 | 7.9981 → 7.9981 | 8.0001 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `lattice-rows-joint` | 25,169,682 → 25,258,810 (-0.35%) | 25,166,413 → 25,312,688 (-0.58%) | 25,167,136 → 25,300,180 (-0.53%) |
| `lattice-rows-route-select` | 25,169,682 → 25,170,174 (-0.00%) | 25,166,413 → 25,166,905 (-0.00%) | 25,167,136 → 25,167,628 (-0.00%) |
| `lattice-rows-select` | 25,169,682 → 25,170,174 (-0.00%) | 25,166,413 → 25,166,905 (-0.00%) | 25,167,136 → 25,167,628 (-0.00%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-direct` | 25,166,052 | -228 | 0.748 | 0.484 | — / — |
| `lattice-direct-xz` | 25,166,052 | -228 | 39.466 | 1.363 | 70,580 / 34,392 |
| `lattice-direct19` | 25,166,052 | -228 | 30.248 | 2.065 | 56,464 / 34,896 |
| `lattice-joint` | 25,166,052 | -228 | 63.439 | 0.686 | — / — |
| `lattice-joint-xz` | 25,166,052 | -228 | 252.481 | 1.206 | 88,368 / 36,904 |
| `lattice-joint19` | 25,166,052 | -228 | 260.682 | 1.701 | 77,764 / 36,688 |
| `lattice-layout` | 25,166,052 | -228 | 7.001 | 0.673 | — / — |
| `lattice-predict` | 25,166,052 | -228 | 4.961 | 0.739 | — / — |
| `lattice-rows-joint` | 25,312,692 | -146,868 | 3.036 | 4.063 | 111,584 / 39,628 |
| `lattice-rows-route-select` | 25,166,909 | -1,085 | 9.383 | 0.545 | 115,228 / 37,936 |
| `lattice-rows-select` | 25,166,909 | -1,085 | 10.112 | 0.655 | 115,068 / 35,788 |

Same-input baseline archives (bytes) · XZ 9 extreme 25,167,136 · Zstandard 19 25,166,414 · Zstandard 3 25,166,414

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#uniform)

</details>

<details>
<summary>walk-distances · 21,155,400 raw bytes</summary>

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-joint19` | 8,773,798 | +12,381,602 | 111.643 | 1.557 | 84,520 / 44,904 |

Same-input baseline archives (bytes) · XZ 9 extreme 17,954,172 · Zstandard 19 19,976,964 · Zstandard 3 20,717,883

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#walk-distances)

</details>

<details>
<summary>webster · 41,458,703 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `lattice-rows-joint` | 41,460,349 | 4.9707 → 6.7647 | 3.4171 → 5.8431 | 6.7650 |
| `lattice-rows-select` | 41,459,510 | 4.9707 → 4.9710 | 3.4171 → 3.4171 | 4.9711 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `lattice-rows-joint` | 12,201,972 → 34,381,121 (-181.77%) | 12,107,194 → 34,326,394 (-183.52%) | 8,628,848 → 31,185,636 (-261.41%) |
| `lattice-rows-select` | 12,201,972 → 12,204,071 (-0.02%) | 12,107,194 → 12,109,357 (-0.02%) | 8,628,848 → 8,629,872 (-0.01%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-rows-joint` | 34,320,561 | +7,138,142 | 2.665 | 1.928 | 144,700 / 41,068 |
| `lattice-rows-select` | 12,097,762 | +29,360,941 | 13.864 | 0.700 | 104,176 / 36,136 |

Same-input baseline archives (bytes) · XZ 9 extreme 8,368,672 · Zstandard 19 8,679,705 · Zstandard 3 12,107,198

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#webster)

</details>

<details>
<summary>wiki-transfer · 25,165,824 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `lattice-rows-field-positions` | 25,215,468 | 5.0850 → 5.0990 | 3.8807 → 4.3003 | 5.1090 |
| `lattice-rows-field-prefix` | 24,571,696 | 5.0850 → 5.1774 | 3.8807 → 3.8770 | 5.0552 |
| `lattice-rows-fields` | 25,169,388 | 5.0850 → 5.0863 | 3.8807 → 3.8892 | 5.0870 |
| `lattice-rows-joint` | 25,275,908 | 5.0850 → 6.2922 | 3.8807 → 5.3031 | 6.3197 |
| `lattice-rows-prefix` | 24,810,563 | 5.0850 → 5.1749 | 3.8807 → 3.8635 | 5.1019 |
| `lattice-rows-route-select` | 25,166,636 | 5.0850 → 5.0854 | 3.8807 → 3.8828 | 5.0855 |
| `lattice-rows-select` | 25,166,316 | 5.0850 → 5.0852 | 3.8807 → 3.8807 | 5.0853 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `lattice-rows-field-positions` | 9,232,082 → 11,665,311 (-26.36%) | 8,968,455 → 11,111,894 (-23.90%) | 6,743,812 → 8,923,908 (-32.33%) |
| `lattice-rows-field-prefix` | 9,232,082 → 9,809,440 (-6.25%) | 8,968,455 → 9,262,307 (-3.28%) | 6,743,812 → 6,962,968 (-3.25%) |
| `lattice-rows-fields` | 9,232,082 → 9,753,222 (-5.64%) | 8,968,455 → 9,166,657 (-2.21%) | 6,743,812 → 6,908,720 (-2.45%) |
| `lattice-rows-joint` | 9,232,082 → 16,107,898 (-74.48%) | 8,968,455 → 15,754,527 (-75.67%) | 6,743,812 → 13,236,764 (-96.28%) |
| `lattice-rows-prefix` | 9,232,082 → 9,339,483 (-1.16%) | 8,968,455 → 9,089,552 (-1.35%) | 6,743,812 → 6,824,684 (-1.20%) |
| `lattice-rows-route-select` | 9,232,082 → 9,268,308 (-0.39%) | 8,968,455 → 8,987,947 (-0.22%) | 6,743,812 → 6,763,280 (-0.29%) |
| `lattice-rows-select` | 9,232,082 → 9,233,599 (-0.02%) | 8,968,455 → 8,968,995 (-0.01%) | 6,743,812 → 6,744,120 (-0.00%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `lattice-direct` | 9,108,718 | +16,057,106 | 0.375 | 0.262 | — / — |
| `lattice-direct-xz` | 7,602,472 | +17,563,352 | 35.643 | 1.807 | 70,748 / 46,052 |
| `lattice-direct19` | 7,824,376 | +17,341,448 | 38.484 | 1.112 | 57,684 / 39,504 |
| `lattice-joint` | 9,108,718 | +16,057,106 | 32.775 | 0.255 | — / — |
| `lattice-joint-xz` | 7,602,472 | +17,563,352 | 144.431 | 1.148 | 87,944 / 46,484 |
| `lattice-joint19` | 7,824,376 | +17,341,448 | 183.325 | 1.182 | 79,868 / 39,244 |
| `lattice-layout` | 9,108,718 | +16,057,106 | 3.042 | 0.251 | — / — |
| `lattice-predict` | 9,108,718 | +16,057,106 | 5.836 | 0.256 | — / — |
| `lattice-rows-field-positions` | 11,108,131 | +14,057,693 | 1.571 | 0.874 | 81,696 / 36,652 |
| `lattice-rows-field-prefix` | 9,257,618 | +15,908,206 | 0.663 | 0.399 | 79,124 / 38,980 |
| `lattice-rows-fields` | 9,169,822 | +15,996,002 | 0.615 | 0.408 | 79,916 / 38,928 |
| `lattice-rows-joint` | 15,741,722 | +9,424,102 | 3.032 | 2.611 | 94,440 / 40,892 |
| `lattice-rows-prefix` | 9,083,523 | +16,082,301 | 0.556 | 0.319 | 78,220 / 39,060 |
| `lattice-rows-route-select` | 8,983,638 | +16,182,186 | 17.545 | 0.623 | 82,572 / 36,708 |
| `lattice-rows-select` | 8,962,957 | +16,202,867 | 10.491 | 0.618 | 81,420 / 36,260 |

Same-input baseline archives (bytes) · XZ 9 extreme 6,637,336 · Zstandard 19 6,891,038 · Zstandard 3 8,968,456

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#wiki-transfer)

</details>

<!-- END generated project measurements -->

## Connections

Compare with [integer wavelets](../reversible-wavelets/README.md), [shape contexts](../shape-context/README.md) and the [distance geometry](../distance-geometry/README.md) model for triangular layouts.
