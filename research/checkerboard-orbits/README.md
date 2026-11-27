# A shared clock for 8 × 8 checkerboard automata

[View this project's benchmark tables](#large-file-benchmark)

## Question and prior work

If many matrices lie on an orbit, is it cheaper to choose the sparsest predecessor of each matrix or to send one time for an entire page?

A second experiment moves the two-phase update onto full-width document strips and splits the resulting matrix into quadrants. It compares a fixed inverse with a scanline predictor and prices a shared dictionary of 8 × 8 leaves. [Bitmap trees and the rotated-rule control](bitmap-trees.md)

### Source files and compatibility

The toroidal checkerboard rule follows `lab/hutter/automa-8x8-passo-byte` and its orbit reports 004–005. The native CBO1 search extends the clock to 1,000 and supports both per-word and page-wide times.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/checkerboard-orbits/control.py runs/shared-clock.bin
python3 research/checkerboard-orbits/codec.py encode runs/shared-clock.bin runs/clock.cbo --profile joint
python3 research/checkerboard-orbits/codec.py decode runs/clock.cbo runs/clock.restored
cmp runs/shared-clock.bin runs/clock.restored
```

## Variants and format

Every 8-byte word holds one toroidal 8×8 matrix. The per-word search examines times 0 through 1,000 and sends exact 16-bit times in two lanes. The shared variant traverses the same 1,001 times on up to 192 dispersed matrices per 256 KiB page and tests the three most promising times by full compressed size. A page selects literal, direct, shared or individual coding. The inverse applies the recorded forward steps.

## Inputs and measurement

The 24 MiB synthetic stream evolves independent sparse seeds. Each page uses one of 37, 113, 509 or 997 steps. Numerical bytes and independent noise are transfer controls. The source contains fresh seeds throughout.

## Results

On the shared-clock control the direct archive used 21,999,209 bytes, per-matrix times 13,612,025 and one page-wide time 12,415,836. All profiles tied on the natural numerical data and on uniform noise. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `shared-orbit-1000` (25,165,824 raw bytes), `checker-joint` produced 12,415,836 archive bytes. [Input and timing](../large-scale/results/by-dataset.md#shared-orbit-1000) · [All project measurements](../large-scale/results/by-experiment.md#checkerboard-orbits)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

H0 measures byte frequencies. H1 conditions on the previous byte. Both use bits per byte of their own stream. Post H0 per raw byte accounts for changes in stream length. In the paired compressor tables, a positive percentage means preprocessing made the compressed file smaller.

### shared-orbit-1000 · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `checker-direct` | 21,999,209 | +3,166,615 | 1.025 | 0.904 |
| `checker-individual` | 13,612,025 | +11,553,799 | 70.204 | 14.477 |
| `checker-joint` | 12,415,836 | +12,749,988 | 136.944 | 23.954 |
| `checker-shared` | 12,415,836 | +12,749,988 | 81.122 | 21.788 |

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#shared-orbit-1000)

<details>
<summary>evolved-stamps · 28,311,552 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 4,829,851 | 1.9696 → 6.4078 | 1.9232 → 4.6752 | 1.0931 |
| `checker-bitmap-direct-flat` | 28,314,124 | 1.9696 → 1.9696 | 1.9232 → 1.9232 | 1.9698 |
| `checker-bitmap-direct-tree` | 9,593,235 | 1.9696 → 5.2001 | 1.9232 → 2.3533 | 1.7620 |
| `checker-bitmap-orbit-book` | 885,494 | 1.9696 → 6.9038 | 1.9232 → 5.3183 | 0.2159 |
| `checker-bitmap-orbit-flat` | 28,314,124 | 1.9696 → 1.4372 | 1.9232 → 1.4113 | 1.4373 |
| `checker-bitmap-orbit-hot` | 884,982 | 1.9696 → 6.8986 | 1.9232 → 5.3806 | 0.2156 |
| `checker-bitmap-orbit-hotplanes` | 884,982 | 1.9696 → 6.8982 | 1.9232 → 5.9038 | 0.2156 |
| `checker-bitmap-orbit-planes` | 3,849,414 | 1.9696 → 7.3016 | 1.9232 → 5.7304 | 0.9928 |
| `checker-bitmap-orbit-tree` | 3,849,414 | 1.9696 → 7.3024 | 1.9232 → 2.0626 | 0.9929 |
| `checker-bitmap-rotated-book` | 10,114,461 | 1.9696 → 6.0024 | 1.9232 → 4.8330 | 2.1444 |
| `checker-bitmap-select` | 885,494 | 1.9696 → 6.9038 | 1.9232 → 5.3183 | 0.2159 |
| `checker-bitmap-xor-book` | 5,092,083 | 1.9696 → 6.4980 | 1.9232 → 4.8623 | 1.1687 |
| `checker-bitmap-xor-flat` | 28,314,124 | 1.9696 → 2.0309 | 1.9232 → 1.9871 | 2.0311 |
| `checker-bitmap-xor-tree` | 9,593,235 | 1.9696 → 5.2846 | 1.9232 → 2.6072 | 1.7906 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `checker-bitmap-direct-book` | 9,023,243 → 2,754,721 (+69.47%) | 9,210,659 → 2,654,150 (+71.18%) | 7,530,660 → 2,120,388 (+71.84%) |
| `checker-bitmap-direct-flat` | 9,023,243 → 9,024,278 (-0.01%) | 9,210,659 → 9,212,352 (-0.02%) | 7,530,660 → 7,526,840 (+0.05%) |
| `checker-bitmap-direct-tree` | 9,023,243 → 2,958,588 (+67.21%) | 9,210,659 → 2,700,418 (+70.68%) | 7,530,660 → 1,975,876 (+73.76%) |
| `checker-bitmap-orbit-book` | 9,023,243 → 623,735 (+93.09%) | 9,210,659 → 622,700 (+93.24%) | 7,530,660 → 560,916 (+92.55%) |
| `checker-bitmap-orbit-flat` | 9,023,243 → 6,884,881 (+23.70%) | 9,210,659 → 7,130,259 (+22.59%) | 7,530,660 → 5,485,804 (+27.15%) |
| `checker-bitmap-orbit-hot` | 9,023,243 → 653,696 (+92.76%) | 9,210,659 → 646,407 (+92.98%) | 7,530,660 → 585,652 (+92.22%) |
| `checker-bitmap-orbit-hotplanes` | 9,023,243 → 767,416 (+91.50%) | 9,210,659 → 766,811 (+91.67%) | 7,530,660 → 693,544 (+90.79%) |
| `checker-bitmap-orbit-planes` | 9,023,243 → 3,490,104 (+61.32%) | 9,210,659 → 3,534,488 (+61.63%) | 7,530,660 → 3,076,668 (+59.14%) |
| `checker-bitmap-orbit-tree` | 9,023,243 → 781,611 (+91.34%) | 9,210,659 → 807,400 (+91.23%) | 7,530,660 → 628,356 (+91.66%) |
| `checker-bitmap-rotated-book` | 9,023,243 → 5,577,984 (+38.18%) | 9,210,659 → 5,366,106 (+41.74%) | 7,530,660 → 4,102,704 (+45.52%) |
| `checker-bitmap-select` | 9,023,243 → 623,735 (+93.09%) | 9,210,659 → 622,700 (+93.24%) | 7,530,660 → 560,916 (+92.55%) |
| `checker-bitmap-xor-book` | 9,023,243 → 2,945,054 (+67.36%) | 9,210,659 → 2,823,988 (+69.34%) | 7,530,660 → 2,275,564 (+69.78%) |
| `checker-bitmap-xor-flat` | 9,023,243 → 9,322,938 (-3.32%) | 9,210,659 → 9,509,890 (-3.25%) | 7,530,660 → 7,732,272 (-2.68%) |
| `checker-bitmap-xor-tree` | 9,023,243 → 3,117,274 (+65.45%) | 9,210,659 → 2,784,689 (+69.77%) | 7,530,660 → 2,084,084 (+72.33%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 2,654,223 | +25,657,329 | 0.279 | 0.321 | 43,796 / 36,164 |
| `checker-bitmap-direct-flat` | 9,211,051 | +19,100,501 | 0.458 | 0.237 | 78,788 / 35,268 |
| `checker-bitmap-direct-tree` | 2,697,447 | +25,614,105 | 0.314 | 0.396 | 49,652 / 38,160 |
| `checker-bitmap-orbit-book` | 622,703 | +27,688,849 | 0.916 | 0.757 | 36,716 / 35,244 |
| `checker-bitmap-orbit-flat` | 7,132,908 | +21,178,644 | 1.223 | 0.716 | 77,040 / 36,360 |
| `checker-bitmap-orbit-hot` | 646,410 | +27,665,142 | 1.442 | 1.178 | 37,060 / 35,596 |
| `checker-bitmap-orbit-hotplanes` | 766,814 | +27,544,738 | 1.760 | 1.275 | 37,252 / 35,524 |
| `checker-bitmap-orbit-planes` | 3,534,224 | +24,777,328 | 1.461 | 1.277 | 43,748 / 36,668 |
| `checker-bitmap-orbit-tree` | 808,254 | +27,503,298 | 0.769 | 0.905 | 38,904 / 36,372 |
| `checker-bitmap-rotated-book` | 5,361,414 | +22,950,138 | 1.851 | 1.285 | 60,604 / 40,512 |
| `checker-bitmap-select` | 622,703 | +27,688,849 | 4.547 | 0.709 | 38,012 / 35,176 |
| `checker-bitmap-xor-book` | 2,823,895 | +25,487,657 | 0.827 | 0.835 | 46,444 / 38,024 |
| `checker-bitmap-xor-flat` | 9,512,240 | +18,799,312 | 0.451 | 0.319 | 81,512 / 37,796 |
| `checker-bitmap-xor-tree` | 2,780,872 | +25,530,680 | 0.360 | 0.495 | 51,832 / 36,176 |

Same-input baseline archives (bytes) · Zstandard 3 9,210,663

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#evolved-stamps)

</details>

<details>
<summary>graphs-shuffled-lines · 24,642,792 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 7,403,073 | 0.7646 → 4.1137 | 0.5291 → 3.6116 | 1.2358 |
| `checker-bitmap-direct-flat` | 24,650,434 | 0.7646 → 0.7646 | 0.5291 → 0.5292 | 0.7649 |
| `checker-bitmap-direct-tree` | 9,598,949 | 0.7646 → 2.0176 | 0.5291 → 1.8635 | 0.7859 |
| `checker-bitmap-orbit-book` | 10,298,117 | 0.7646 → 5.7467 | 0.5291 → 4.8523 | 2.4015 |
| `checker-bitmap-select` | 24,650,434 | 0.7646 → 0.7646 | 0.5291 → 0.5292 | 0.7649 |
| `checker-bitmap-xor-flat` | 24,650,434 | 0.7646 → 1.3353 | 0.5291 → 0.9789 | 1.3358 |
| `checker-bitmap-xor-hotplanes` | 7,200,199 | 0.7646 → 4.0479 | 0.5291 → 3.3618 | 1.1827 |
| `checker-bitmap-xor-tree` | 10,244,921 | 0.7646 → 3.0310 | 0.5291 → 2.2780 | 1.2601 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `checker-bitmap-direct-book` | 2,036,986 → 3,536,239 (-73.60%) | 1,849,713 → 3,606,684 (-94.99%) | 1,380,120 → 2,771,044 (-100.78%) |
| `checker-bitmap-direct-flat` | 2,036,986 → 2,039,106 (-0.10%) | 1,849,713 → 1,851,560 (-0.10%) | 1,380,120 → 1,392,196 (-0.87%) |
| `checker-bitmap-direct-tree` | 2,036,986 → 2,674,340 (-31.29%) | 1,849,713 → 2,826,361 (-52.80%) | 1,380,120 → 1,991,168 (-44.27%) |
| `checker-bitmap-orbit-book` | 2,036,986 → 6,223,539 (-205.53%) | 1,849,713 → 6,280,069 (-239.52%) | 1,380,120 → 4,865,512 (-252.54%) |
| `checker-bitmap-select` | 2,036,986 → 2,039,106 (-0.10%) | 1,849,713 → 1,851,560 (-0.10%) | 1,380,120 → 1,392,196 (-0.87%) |
| `checker-bitmap-xor-flat` | 2,036,986 → 2,576,199 (-26.47%) | 1,849,713 → 2,408,779 (-30.22%) | 1,380,120 → 1,844,152 (-33.62%) |
| `checker-bitmap-xor-hotplanes` | 2,036,986 → 3,010,554 (-47.79%) | 1,849,713 → 2,933,192 (-58.58%) | 1,380,120 → 2,612,392 (-89.29%) |
| `checker-bitmap-xor-tree` | 2,036,986 → 3,349,886 (-64.45%) | 1,849,713 → 3,492,995 (-88.84%) | 1,380,120 → 2,593,716 (-87.93%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 3,608,591 | +21,034,201 | 0.630 | 0.583 | 48,192 / 35,932 |
| `checker-bitmap-direct-flat` | 1,846,387 | +22,796,405 | 0.382 | 0.317 | 60,428 / 35,544 |
| `checker-bitmap-direct-tree` | 2,827,555 | +21,815,237 | 0.670 | 0.452 | 47,912 / 36,400 |
| `checker-bitmap-orbit-book` | 6,277,729 | +18,365,063 | 1.089 | 0.668 | 58,048 / 36,640 |
| `checker-bitmap-select` | 1,846,387 | +22,796,405 | 4.017 | 0.256 | 62,424 / 37,792 |
| `checker-bitmap-xor-flat` | 2,405,283 | +22,237,509 | 0.461 | 0.502 | 61,780 / 37,628 |
| `checker-bitmap-xor-hotplanes` | 2,933,196 | +21,709,596 | 1.155 | 1.222 | 47,480 / 36,212 |
| `checker-bitmap-xor-tree` | 3,492,002 | +21,150,790 | 1.014 | 1.008 | 50,000 / 36,316 |

Same-input baseline archives (bytes) · Zstandard 3 1,849,717

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#graphs-shuffled-lines)

</details>

<details>
<summary>manual-graphs · 24,642,792 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 2,850,113 | 0.7646 → 5.4081 | 0.5291 → 4.0221 | 0.6255 |
| `checker-bitmap-direct-flat` | 24,650,434 | 0.7646 → 0.7646 | 0.5291 → 0.5292 | 0.7649 |
| `checker-bitmap-direct-hot` | 2,531,379 | 0.7646 → 4.7870 | 0.5291 → 3.2825 | 0.4917 |
| `checker-bitmap-direct-hotplanes` | 2,531,379 | 0.7646 → 4.7870 | 0.5291 → 4.1411 | 0.4917 |
| `checker-bitmap-direct-planes` | 2,926,539 | 0.7646 → 4.6161 | 0.5291 → 3.6930 | 0.5482 |
| `checker-bitmap-direct-tree` | 2,926,539 | 0.7646 → 4.6152 | 0.5291 → 2.9137 | 0.5481 |
| `checker-bitmap-orbit-book` | 3,323,668 | 0.7646 → 5.8915 | 0.5291 → 5.1405 | 0.7946 |
| `checker-bitmap-orbit-flat` | 24,650,434 | 0.7646 → 0.9611 | 0.5291 → 0.6964 | 0.9614 |
| `checker-bitmap-orbit-tree` | 3,393,558 | 0.7646 → 5.1915 | 0.5291 → 4.1933 | 0.7149 |
| `checker-bitmap-select` | 6,123,631 | 0.7646 → 2.0863 | 0.5291 → 1.6433 | 0.5184 |
| `checker-bitmap-xor-book` | 2,920,517 | 0.7646 → 4.6615 | 0.5291 → 4.0528 | 0.5524 |
| `checker-bitmap-xor-flat` | 24,650,434 | 0.7646 → 0.5581 | 0.5291 → 0.4053 | 0.5583 |
| `checker-bitmap-xor-hot` | 2,608,143 | 0.7646 → 3.8982 | 0.5291 → 3.3043 | 0.4126 |
| `checker-bitmap-xor-hotplanes` | 2,608,143 | 0.7646 → 3.8980 | 0.5291 → 3.4410 | 0.4126 |
| `checker-bitmap-xor-planes` | 2,904,414 | 0.7646 → 3.7019 | 0.5291 → 2.9840 | 0.4363 |
| `checker-bitmap-xor-tree` | 2,904,414 | 0.7646 → 3.7017 | 0.5291 → 2.9808 | 0.4363 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `checker-bitmap-direct-book` | 1,520,849 → 1,464,931 (+3.68%) | 1,325,130 → 1,389,866 (-4.89%) | 1,004,072 → 1,076,292 (-7.19%) |
| `checker-bitmap-direct-flat` | 1,520,849 → 1,523,258 (-0.16%) | 1,325,130 → 1,328,836 (-0.28%) | 1,004,072 → 1,008,172 (-0.41%) |
| `checker-bitmap-direct-hot` | 1,520,849 → 1,139,557 (+25.07%) | 1,325,130 → 1,046,567 (+21.02%) | 1,004,072 → 796,608 (+20.66%) |
| `checker-bitmap-direct-hotplanes` | 1,520,849 → 1,356,654 (+10.80%) | 1,325,130 → 1,314,345 (+0.81%) | 1,004,072 → 1,106,104 (-10.16%) |
| `checker-bitmap-direct-planes` | 1,520,849 → 1,326,907 (+12.75%) | 1,325,130 → 1,252,966 (+5.45%) | 1,004,072 → 995,652 (+0.84%) |
| `checker-bitmap-direct-tree` | 1,520,849 → 1,067,575 (+29.80%) | 1,325,130 → 926,450 (+30.09%) | 1,004,072 → 634,084 (+36.85%) |
| `checker-bitmap-orbit-book` | 1,520,849 → 2,009,971 (-32.16%) | 1,325,130 → 1,818,834 (-37.26%) | 1,004,072 → 1,403,424 (-39.77%) |
| `checker-bitmap-orbit-flat` | 1,520,849 → 2,368,383 (-55.73%) | 1,325,130 → 2,163,497 (-63.27%) | 1,004,072 → 1,790,876 (-78.36%) |
| `checker-bitmap-orbit-tree` | 1,520,849 → 1,561,232 (-2.66%) | 1,325,130 → 1,249,242 (+5.73%) | 1,004,072 → 868,944 (+13.46%) |
| `checker-bitmap-select` | 1,520,849 → 1,109,905 (+27.02%) | 1,325,130 → 970,779 (+26.74%) | 1,004,072 → 690,144 (+31.27%) |
| `checker-bitmap-xor-book` | 1,520,849 → 1,479,231 (+2.74%) | 1,325,130 → 1,383,577 (-4.41%) | 1,004,072 → 1,102,620 (-9.81%) |
| `checker-bitmap-xor-flat` | 1,520,849 → 1,513,711 (+0.47%) | 1,325,130 → 1,359,169 (-2.57%) | 1,004,072 → 1,112,424 (-10.79%) |
| `checker-bitmap-xor-hot` | 1,520,849 → 1,125,042 (+26.03%) | 1,325,130 → 1,010,214 (+23.76%) | 1,004,072 → 780,124 (+22.30%) |
| `checker-bitmap-xor-hotplanes` | 1,520,849 → 1,294,290 (+14.90%) | 1,325,130 → 1,273,925 (+3.86%) | 1,004,072 → 1,135,300 (-13.07%) |
| `checker-bitmap-xor-planes` | 1,520,849 → 1,250,981 (+17.74%) | 1,325,130 → 1,201,823 (+9.31%) | 1,004,072 → 1,020,492 (-1.64%) |
| `checker-bitmap-xor-tree` | 1,520,849 → 1,031,081 (+32.20%) | 1,325,130 → 883,342 (+33.34%) | 1,004,072 → 612,788 (+38.97%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 1,389,962 | +23,252,830 | 0.389 | 0.352 | 41,572 / 36,296 |
| `checker-bitmap-direct-flat` | 1,329,615 | +23,313,177 | 0.242 | 0.174 | 59,612 / 37,400 |
| `checker-bitmap-direct-hot` | 1,046,571 | +23,596,221 | 0.808 | 0.987 | 39,120 / 36,740 |
| `checker-bitmap-direct-hotplanes` | 1,314,349 | +23,328,443 | 0.632 | 1.033 | 39,708 / 36,624 |
| `checker-bitmap-direct-planes` | 1,252,789 | +23,390,003 | 0.909 | 0.610 | 38,696 / 36,576 |
| `checker-bitmap-direct-tree` | 926,786 | +23,716,006 | 0.348 | 0.349 | 38,036 / 36,312 |
| `checker-bitmap-orbit-book` | 1,818,813 | +22,823,979 | 1.042 | 0.819 | 42,812 / 36,528 |
| `checker-bitmap-orbit-flat` | 2,159,692 | +22,483,100 | 0.452 | 0.452 | 61,436 / 38,248 |
| `checker-bitmap-orbit-tree` | 1,249,131 | +23,393,661 | 0.692 | 0.904 | 41,380 / 36,692 |
| `checker-bitmap-select` | 971,085 | +23,671,707 | 2.647 | 0.438 | 43,544 / 36,064 |
| `checker-bitmap-xor-book` | 1,383,476 | +23,259,316 | 0.329 | 0.312 | 41,180 / 38,420 |
| `checker-bitmap-xor-flat` | 1,357,152 | +23,285,640 | 0.273 | 0.190 | 59,940 / 35,564 |
| `checker-bitmap-xor-hot` | 1,010,218 | +23,632,574 | 0.924 | 0.851 | 39,184 / 36,676 |
| `checker-bitmap-xor-hotplanes` | 1,273,929 | +23,368,863 | 1.544 | 0.908 | 40,648 / 36,648 |
| `checker-bitmap-xor-planes` | 1,202,135 | +23,440,657 | 0.665 | 0.771 | 38,836 / 36,124 |
| `checker-bitmap-xor-tree` | 883,584 | +23,759,208 | 0.279 | 0.330 | 40,468 / 36,112 |

Same-input baseline archives (bytes) · DjVu 214,067 · DjVu (separated foreground) 213,732 · DjVu (wide strips) 191,132 · CCITT Group 4 1,270,850 · JBIG 707,797 · 1-bit PNG 1,418,635 · XZ 9 extreme 930,864 · Zstandard 19 1,034,431 · Zstandard 3 1,325,134

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#manual-graphs)

</details>

<details>
<summary>manual-library · 24,283,584 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 3,978,731 | 1.0898 → 5.5074 | 0.7688 → 4.0516 | 0.9024 |
| `checker-bitmap-direct-tree` | 4,329,338 | 1.0898 → 4.5936 | 0.7688 → 2.8490 | 0.8190 |
| `checker-bitmap-orbit-book` | 4,623,892 | 1.0898 → 5.9495 | 0.7688 → 5.1475 | 1.1329 |
| `checker-bitmap-select` | 5,661,943 | 1.0898 → 3.0788 | 0.7688 → 2.4187 | 0.7179 |
| `checker-bitmap-xor-book` | 4,064,989 | 1.0898 → 4.7625 | 0.7688 → 4.0913 | 0.7972 |
| `checker-bitmap-xor-flat` | 24,290,980 | 1.0898 → 0.7858 | 0.7688 → 0.5951 | 0.7861 |
| `checker-bitmap-xor-hot` | 3,703,395 | 1.0898 → 4.0059 | 0.7688 → 3.3646 | 0.6109 |
| `checker-bitmap-xor-hotplanes` | 3,703,395 | 1.0898 → 4.0058 | 0.7688 → 3.5299 | 0.6109 |
| `checker-bitmap-xor-planes` | 4,312,007 | 1.0898 → 3.6490 | 0.7688 → 2.9694 | 0.6479 |
| `checker-bitmap-xor-tree` | 4,312,007 | 1.0898 → 3.6489 | 0.7688 → 2.9336 | 0.6479 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `checker-bitmap-direct-book` | 2,189,641 → 2,053,017 (+6.24%) | 1,903,362 → 1,891,562 (+0.62%) | 1,375,968 → 1,420,104 (-3.21%) |
| `checker-bitmap-direct-tree` | 2,189,641 → 1,537,629 (+29.78%) | 1,903,362 → 1,219,247 (+35.94%) | 1,375,968 → 739,252 (+46.27%) |
| `checker-bitmap-orbit-book` | 2,189,641 → 2,804,192 (-28.07%) | 1,903,362 → 2,422,699 (-27.29%) | 1,375,968 → 1,787,632 (-29.92%) |
| `checker-bitmap-select` | 2,189,641 → 1,562,357 (+28.65%) | 1,903,362 → 1,260,597 (+33.77%) | 1,375,968 → 804,356 (+41.54%) |
| `checker-bitmap-xor-book` | 2,189,641 → 2,069,896 (+5.47%) | 1,903,362 → 1,884,878 (+0.97%) | 1,375,968 → 1,450,876 (-5.44%) |
| `checker-bitmap-xor-flat` | 2,189,641 → 2,172,094 (+0.80%) | 1,903,362 → 1,920,038 (-0.88%) | 1,375,968 → 1,499,812 (-9.00%) |
| `checker-bitmap-xor-hot` | 2,189,641 → 1,610,206 (+26.46%) | 1,903,362 → 1,382,633 (+27.36%) | 1,375,968 → 1,020,688 (+25.82%) |
| `checker-bitmap-xor-hotplanes` | 2,189,641 → 1,888,003 (+13.78%) | 1,903,362 → 1,854,681 (+2.56%) | 1,375,968 → 1,635,116 (-18.83%) |
| `checker-bitmap-xor-planes` | 2,189,641 → 1,864,803 (+14.84%) | 1,903,362 → 1,745,729 (+8.28%) | 1,375,968 → 1,417,244 (-3.00%) |
| `checker-bitmap-xor-tree` | 2,189,641 → 1,480,008 (+32.41%) | 1,903,362 → 1,162,886 (+38.90%) | 1,375,968 → 717,328 (+47.87%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 1,891,255 | +22,392,329 | 0.648 | 0.550 | 43,260 / 36,048 |
| `checker-bitmap-direct-tree` | 1,219,251 | +23,064,333 | 0.773 | 0.539 | 40,024 / 36,504 |
| `checker-bitmap-orbit-book` | 2,422,761 | +21,860,823 | 0.929 | 0.698 | 42,996 / 36,284 |
| `checker-bitmap-select` | 1,260,415 | +23,023,169 | 2.895 | 0.613 | 43,288 / 36,148 |
| `checker-bitmap-xor-book` | 1,884,392 | +22,399,192 | 0.775 | 0.661 | 43,868 / 36,184 |
| `checker-bitmap-xor-flat` | 1,914,406 | +22,369,178 | 0.571 | 0.430 | 60,452 / 35,564 |
| `checker-bitmap-xor-hot` | 1,382,637 | +22,900,947 | 0.833 | 0.769 | 40,940 / 36,720 |
| `checker-bitmap-xor-hotplanes` | 1,854,685 | +22,428,899 | 0.651 | 0.825 | 41,904 / 36,792 |
| `checker-bitmap-xor-planes` | 1,745,733 | +22,537,851 | 0.766 | 0.935 | 41,508 / 36,500 |
| `checker-bitmap-xor-tree` | 1,162,890 | +23,120,694 | 0.714 | 0.911 | 40,076 / 36,288 |

Same-input baseline archives (bytes) · DjVu 202,780 · DjVu (separated foreground) 202,666 · DjVu (wide strips) 175,164 · CCITT Group 4 1,678,602 · JBIG 1,049,864 · 1-bit PNG 1,996,848 · XZ 9 extreme 1,304,420 · Zstandard 19 1,457,017 · Zstandard 3 1,903,366

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#manual-library)

</details>

<details>
<summary>manual-transfer · 31,809,024 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 4,542,839 | 0.9931 → 5.4695 | 0.6449 → 3.8703 | 0.7811 |
| `checker-bitmap-direct-tree` | 5,197,543 | 0.9931 → 4.4275 | 0.6449 → 2.6278 | 0.7235 |
| `checker-bitmap-orbit-book` | 5,251,862 | 0.9931 → 5.9091 | 0.6449 → 4.9348 | 0.9756 |
| `checker-bitmap-select` | 13,353,597 | 0.9931 → 1.6982 | 0.6449 → 1.3089 | 0.7129 |
| `checker-bitmap-xor-book` | 4,537,674 | 0.9931 → 4.6357 | 0.6449 → 3.9871 | 0.6613 |
| `checker-bitmap-xor-flat` | 31,811,916 | 0.9931 → 0.6563 | 0.6449 → 0.5019 | 0.6563 |
| `checker-bitmap-xor-hot` | 4,023,794 | 0.9931 → 4.0289 | 0.6449 → 3.4131 | 0.5097 |
| `checker-bitmap-xor-hotplanes` | 4,023,794 | 0.9931 → 4.0286 | 0.6449 → 3.5358 | 0.5096 |
| `checker-bitmap-xor-planes` | 5,128,749 | 0.9931 → 3.3440 | 0.6449 → 2.6874 | 0.5392 |
| `checker-bitmap-xor-tree` | 5,128,749 | 0.9931 → 3.3438 | 0.6449 → 2.7025 | 0.5391 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `checker-bitmap-direct-book` | 2,229,879 → 2,196,335 (+1.50%) | 2,005,044 → 2,061,438 (-2.81%) | 1,468,704 → 1,534,596 (-4.49%) |
| `checker-bitmap-direct-tree` | 2,229,879 → 1,597,548 (+28.36%) | 2,005,044 → 1,360,567 (+32.14%) | 1,468,704 → 801,760 (+45.41%) |
| `checker-bitmap-orbit-book` | 2,229,879 → 2,946,901 (-32.16%) | 2,005,044 → 2,604,989 (-29.92%) | 1,468,704 → 1,924,348 (-31.02%) |
| `checker-bitmap-select` | 2,229,879 → 1,719,298 (+22.90%) | 2,005,044 → 1,495,485 (+25.41%) | 1,468,704 → 973,176 (+33.74%) |
| `checker-bitmap-xor-book` | 2,229,879 → 2,170,895 (+2.65%) | 2,005,044 → 2,025,025 (-1.00%) | 1,468,704 → 1,551,548 (-5.64%) |
| `checker-bitmap-xor-flat` | 2,229,879 → 2,217,736 (+0.54%) | 2,005,044 → 1,992,156 (+0.64%) | 1,468,704 → 1,566,396 (-6.65%) |
| `checker-bitmap-xor-hot` | 2,229,879 → 1,701,213 (+23.71%) | 2,005,044 → 1,534,895 (+23.45%) | 1,468,704 → 1,142,092 (+22.24%) |
| `checker-bitmap-xor-hotplanes` | 2,229,879 → 2,029,164 (+9.00%) | 2,005,044 → 2,023,740 (-0.93%) | 1,468,704 → 1,783,448 (-21.43%) |
| `checker-bitmap-xor-planes` | 2,229,879 → 1,935,600 (+13.20%) | 2,005,044 → 1,847,808 (+7.84%) | 1,468,704 → 1,511,756 (-2.93%) |
| `checker-bitmap-xor-tree` | 2,229,879 → 1,508,593 (+32.35%) | 2,005,044 → 1,307,011 (+34.81%) | 1,468,704 → 774,040 (+47.30%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 2,061,234 | +29,747,790 | 0.403 | 0.370 | 42,660 / 36,296 |
| `checker-bitmap-direct-tree` | 1,360,571 | +30,448,453 | 0.640 | 1.017 | 41,168 / 36,480 |
| `checker-bitmap-orbit-book` | 2,604,929 | +29,204,095 | 0.598 | 0.482 | 46,172 / 38,944 |
| `checker-bitmap-select` | 1,490,218 | +30,318,806 | 1.914 | 0.499 | 52,868 / 36,404 |
| `checker-bitmap-xor-book` | 2,025,143 | +29,783,881 | 0.423 | 0.475 | 42,252 / 38,684 |
| `checker-bitmap-xor-flat` | 1,988,651 | +29,820,373 | 0.234 | 0.133 | 69,308 / 35,848 |
| `checker-bitmap-xor-hot` | 1,534,899 | +30,274,125 | 1.043 | 1.386 | 41,488 / 36,752 |
| `checker-bitmap-xor-hotplanes` | 2,023,744 | +29,785,280 | 1.172 | 1.036 | 42,856 / 36,980 |
| `checker-bitmap-xor-planes` | 1,847,812 | +29,961,212 | 1.048 | 1.512 | 41,908 / 38,540 |
| `checker-bitmap-xor-tree` | 1,307,015 | +30,502,009 | 1.325 | 1.511 | 41,292 / 36,660 |

Same-input baseline archives (bytes) · DjVu 213,659 · DjVu (separated foreground) 213,655 · DjVu (wide strips) 189,610 · JBIG 1,108,897 · XZ 9 extreme 1,354,964 · Zstandard 19 1,525,436

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#manual-transfer)

</details>

<details>
<summary>manual-valgrind · 30,924,288 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 6,350,615 | 1.3043 → 5.5204 | 0.8091 → 4.0915 | 1.1337 |
| `checker-bitmap-direct-tree` | 8,011,199 | 1.3043 → 4.0819 | 0.8091 → 2.5323 | 1.0575 |
| `checker-bitmap-orbit-book` | 7,291,997 | 1.3043 → 6.1036 | 0.8091 → 5.1477 | 1.4392 |
| `checker-bitmap-select` | 14,905,493 | 1.3043 → 2.1255 | 0.8091 → 1.5679 | 1.0245 |
| `checker-bitmap-xor-book` | 6,527,085 | 1.3043 → 4.9093 | 0.8091 → 4.1685 | 1.0362 |
| `checker-bitmap-xor-flat` | 30,927,100 | 1.3043 → 1.0792 | 0.8091 → 0.6600 | 1.0793 |
| `checker-bitmap-xor-hot` | 5,689,159 | 1.3043 → 4.1315 | 0.8091 → 3.3168 | 0.7601 |
| `checker-bitmap-xor-hotplanes` | 5,689,159 | 1.3043 → 4.1314 | 0.8091 → 3.4003 | 0.7601 |
| `checker-bitmap-xor-planes` | 8,128,963 | 1.3043 → 3.4362 | 0.8091 → 2.3048 | 0.9033 |
| `checker-bitmap-xor-tree` | 8,128,963 | 1.3043 → 3.4361 | 0.8091 → 2.7195 | 0.9032 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `checker-bitmap-direct-book` | 2,943,798 → 3,005,449 (-2.09%) | 2,582,180 → 2,769,522 (-7.26%) | 1,908,720 → 2,038,308 (-6.79%) |
| `checker-bitmap-direct-tree` | 2,943,798 → 2,242,189 (+23.83%) | 2,582,180 → 1,787,822 (+30.76%) | 1,908,720 → 1,042,068 (+45.40%) |
| `checker-bitmap-orbit-book` | 2,943,798 → 4,095,977 (-39.14%) | 2,582,180 → 3,568,565 (-38.20%) | 1,908,720 → 2,574,776 (-34.90%) |
| `checker-bitmap-select` | 2,943,798 → 2,412,096 (+18.06%) | 2,582,180 → 2,003,009 (+22.43%) | 1,908,720 → 1,298,608 (+31.96%) |
| `checker-bitmap-xor-book` | 2,943,798 → 3,044,802 (-3.43%) | 2,582,180 → 2,790,503 (-8.07%) | 1,908,720 → 2,106,880 (-10.38%) |
| `checker-bitmap-xor-flat` | 2,943,798 → 3,014,259 (-2.39%) | 2,582,180 → 2,683,089 (-3.91%) | 1,908,720 → 2,112,440 (-10.67%) |
| `checker-bitmap-xor-hot` | 2,943,798 → 2,347,526 (+20.26%) | 2,582,180 → 2,042,660 (+20.89%) | 1,908,720 → 1,462,128 (+23.40%) |
| `checker-bitmap-xor-hotplanes` | 2,943,798 → 2,732,444 (+7.18%) | 2,582,180 → 2,689,270 (-4.15%) | 1,908,720 → 2,369,924 (-24.16%) |
| `checker-bitmap-xor-planes` | 2,943,798 → 2,690,298 (+8.61%) | 2,582,180 → 2,506,790 (+2.92%) | 1,908,720 → 1,998,760 (-4.72%) |
| `checker-bitmap-xor-tree` | 2,943,798 → 2,181,871 (+25.88%) | 2,582,180 → 1,738,730 (+32.66%) | 1,908,720 → 1,025,524 (+46.27%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 2,769,540 | +28,154,748 | 0.725 | 0.639 | 45,376 / 36,396 |
| `checker-bitmap-direct-tree` | 1,787,354 | +29,136,934 | 1.431 | 1.190 | 44,916 / 36,492 |
| `checker-bitmap-orbit-book` | 3,568,143 | +27,356,145 | 1.339 | 1.076 | 48,064 / 36,976 |
| `checker-bitmap-select` | 1,998,256 | +28,926,032 | 3.829 | 0.690 | 55,088 / 38,444 |
| `checker-bitmap-xor-book` | 2,790,929 | +28,133,359 | 0.650 | 0.837 | 46,052 / 36,660 |
| `checker-bitmap-xor-flat` | 2,675,415 | +28,248,873 | 0.489 | 0.571 | 68,332 / 35,844 |
| `checker-bitmap-xor-hot` | 2,042,640 | +28,881,648 | 1.174 | 1.271 | 44,560 / 36,748 |
| `checker-bitmap-xor-hotplanes` | 2,688,919 | +28,235,369 | 1.537 | 1.058 | 45,716 / 36,756 |
| `checker-bitmap-xor-planes` | 2,508,155 | +28,416,133 | 1.050 | 1.050 | 46,504 / 36,424 |
| `checker-bitmap-xor-tree` | 1,738,368 | +29,185,920 | 1.479 | 1.030 | 45,200 / 36,440 |

Same-input baseline archives (bytes) · DjVu 868,904 · DjVu (separated foreground) 869,916 · DjVu (wide strips) 828,622 · JBIG 1,980,581 · XZ 9 extreme 1,795,240 · Zstandard 19 2,032,818

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#manual-valgrind)

</details>

<details>
<summary>numerical · 25,696,748 raw bytes</summary>

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `checker-direct` | 15,272,238 | +10,424,510 | 1.840 | 1.072 |
| `checker-individual` | 15,272,238 | +10,424,510 | 80.420 | 1.598 |
| `checker-joint` | 15,272,238 | +10,424,510 | 172.857 | 1.239 |
| `checker-shared` | 15,272,238 | +10,424,510 | 56.806 | 1.811 |

Same-input baseline archives (bytes) · XZ 9 extreme 11,662,476 · Zstandard 19 13,213,336 · Zstandard 3 15,163,683

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#numerical)

</details>

<details>
<summary>rotated-stamps · 28,311,552 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 4,786,724 | 2.1087 → 6.3996 | 1.5529 → 4.4591 | 1.0820 |
| `checker-bitmap-direct-tree` | 9,660,566 | 2.1087 → 5.1941 | 1.5529 → 2.3352 | 1.7723 |
| `checker-bitmap-orbit-book` | 10,109,056 | 2.1087 → 6.2687 | 1.5529 → 4.9895 | 2.2383 |
| `checker-bitmap-rotated-book` | 885,494 | 2.1087 → 6.9034 | 1.5529 → 5.3186 | 0.2159 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `checker-bitmap-direct-book` | 7,665,858 → 2,246,196 (+70.70%) | 7,867,492 → 2,244,509 (+71.47%) | 5,962,732 → 1,700,168 (+71.49%) |
| `checker-bitmap-direct-tree` | 7,665,858 → 2,116,004 (+72.40%) | 7,867,492 → 2,059,413 (+73.82%) | 5,962,732 → 1,218,712 (+79.56%) |
| `checker-bitmap-orbit-book` | 7,665,858 → 5,673,107 (+26.00%) | 7,867,492 → 5,441,366 (+30.84%) | 5,962,732 → 4,136,800 (+30.62%) |
| `checker-bitmap-rotated-book` | 7,665,858 → 623,741 (+91.86%) | 7,867,492 → 622,584 (+92.09%) | 5,962,732 → 560,832 (+90.59%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 2,244,369 | +26,067,183 | 0.872 | 0.753 | 46,924 / 39,968 |
| `checker-bitmap-direct-tree` | 2,056,730 | +26,254,822 | 0.849 | 0.797 | 50,192 / 39,288 |
| `checker-bitmap-orbit-book` | 5,438,702 | +22,872,850 | 1.126 | 1.099 | 58,616 / 40,336 |
| `checker-bitmap-rotated-book` | 622,587 | +27,688,965 | 0.885 | 0.998 | 40,540 / 39,256 |

Same-input baseline archives (bytes) · Zstandard 3 7,867,496

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#rotated-stamps)

</details>

<details>
<summary>uniform · 25,165,824 raw bytes</summary>

**Entropy before and after preprocessing**

| Profile | Prepared bytes | H0 before → after | H1 before → after | Post H0 per raw byte |
|---|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 31,977,556 | 8.0000 → 7.9274 | 7.9981 → 7.8311 | 10.0731 |
| `checker-bitmap-orbit-book` | 31,977,556 | 8.0000 → 7.9274 | 7.9981 → 7.8312 | 10.0731 |
| `checker-bitmap-select` | 25,168,884 | 8.0000 → 8.0000 | 7.9981 → 7.9980 | 8.0010 |
| `checker-bitmap-xor-flat` | 25,168,884 | 8.0000 → 8.0000 | 7.9981 → 7.9980 | 8.0010 |

**Same compressor on original → prepared bytes**

| Profile | gzip 6 | Zstandard 3 | XZ 6 |
|---|---:|---:|---:|
| `checker-bitmap-direct-book` | 25,169,682 → 31,231,293 (-24.08%) | 25,166,413 → 31,103,267 (-23.59%) | 25,167,136 → 30,331,704 (-20.52%) |
| `checker-bitmap-orbit-book` | 25,169,682 → 31,231,950 (-24.09%) | 25,166,413 → 31,104,010 (-23.59%) | 25,167,136 → 30,346,228 (-20.58%) |
| `checker-bitmap-select` | 25,169,682 → 25,172,017 (-0.01%) | 25,166,413 → 25,168,724 (-0.01%) | 25,167,136 → 25,169,704 (-0.01%) |
| `checker-bitmap-xor-flat` | 25,169,682 → 25,172,234 (-0.01%) | 25,166,413 → 25,168,941 (-0.01%) | 25,167,136 → 25,169,932 (-0.01%) |

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `checker-bitmap-direct-book` | 30,949,326 | -5,783,502 | 1.466 | 0.688 | 127,788 / 38,436 |
| `checker-bitmap-orbit-book` | 30,949,976 | -5,784,152 | 1.458 | 1.002 | 127,496 / 36,316 |
| `checker-bitmap-select` | 25,168,724 | -2,900 | 2.624 | 0.260 | 110,200 / 37,312 |
| `checker-bitmap-xor-flat` | 25,168,943 | -3,119 | 0.407 | 0.362 | 108,680 / 35,696 |
| `checker-direct` | 25,166,508 | -684 | 0.964 | 1.092 | — / — |
| `checker-individual` | 25,166,508 | -684 | 119.437 | 2.317 | — / — |
| `checker-joint` | 25,166,508 | -684 | 193.450 | 0.726 | — / — |
| `checker-shared` | 25,166,508 | -684 | 115.506 | 1.747 | — / — |

Same-input baseline archives (bytes) · XZ 9 extreme 25,167,136 · Zstandard 19 25,166,414 · Zstandard 3 25,166,414

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#uniform)

</details>

<!-- END generated project measurements -->

## Connections

The [3D](../tensor-orbits/README.md) and [4D](../four-dimensional-factors/README.md) projects use different rules and look for low-rank predecessors. Experiment 06 measures two 2D rule families.

## Inspect one torus

The English port of the workspace's `gioca_automa.py` prints each cell in the recorded grid and compares the minimum-entropy predecessor with the smallest complete packet.

```sh
python3 research/checkerboard-orbits/explore.py --recorded --steps 255 --save runs/recorded.torus
python3 research/checkerboard-orbits/explore.py --open runs/recorded.torus
```

In the archived 8 × 8 crop the lowest entropy occurs at step 183, whereas the smallest packet occurs at step 35. Its bytes are `08 08 23 2c 4e 4e e5 a1 d5 32 5d`. This is a format-compatibility vector. The full corpus measurements use independent large inputs.
