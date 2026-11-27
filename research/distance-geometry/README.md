# Distance matrices reconstructed from landmarks

[View this project's benchmark tables](#large-file-benchmark)

## Question and prior work

The old triangle experiment predicted an entry from the row above. Can a decoder recover the geometry itself when it receives only pairwise distances?

### Source files and compatibility

The lower-triangle layout and random-walk control come from `lab/shape/triangle.py`. DGM1 adds a self-contained landmark predictor. The geographic inputs are constructed from actual coordinates in enwik9. They are separate, derived files with independently pinned hashes.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/distance-geometry/codec.py encode runs/large/raw/arc-distances runs/places.dgm --profile all
python3 research/distance-geometry/codec.py decode runs/places.dgm runs/places.restored
cmp runs/large/raw/arc-distances runs/places.restored
```

## Variants and format

For n vertices the file has n(n−1)/2 little-endian unsigned 16-bit entries. The encoder chooses a triangle or tetrahedron of well-spread anchors, then stores their indices and full distance columns. Differences of squared distances give dot products against the anchor simplex. An integer adjugate and a fixed-point inverse predict the remaining pairs. The decoder recovers all errors from signed residual lanes. A separate spherical profile maps angular bins to chord bins using a deterministic Q62 recurrence before predicting, and maps back before applying the residual. The archived integer table is restored exactly; the coordinates stay with the data generator.

## Inputs and measurement

The 4,600 distinct coordinate pairs come from Wikipedia coordinate templates and explicitly signed named infobox fields. One table contains rounded 3D unit-sphere chord distances and another rounded great-circle angles. A seeded planar walk extends the original control. The random control has exactly the same triangular length and row count. Each raw file contains 21,155,400 bytes.

## Results

On the real-place chord table, row prediction gave 14,052,449 bytes, three landmarks gave 14,554,691, four landmarks gave 3,850,014 and XZ extreme gave 16,711,344. On the angular table, blindly applying the Euclidean model gave 14,975,990 bytes. The spherical model gave 4,242,861. On matched random words the selector retained the original data with a 13-byte header. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `place-distances` (21,155,400 raw bytes), `distance-three` produced 3,850,014 archive bytes. Zstandard level 3 used 20,188,613 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#place-distances) · [All project measurements](../large-scale/results/by-experiment.md#distance-geometry)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

### place-distances · 21,155,400 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `distance-direct` | 20,027,877 | +1,127,523 | 2.281 | 1.660 | 93,592 / 94,744 |
| `distance-joint` | 3,850,014 | +17,305,386 | 5.433 | 5.220 | 180,288 / 129,720 |
| `distance-rows` | 14,052,449 | +7,102,951 | 2.484 | 2.845 | 137,868 / 125,716 |
| `distance-three` | 3,850,014 | +17,305,386 | 3.909 | 4.255 | 143,992 / 129,784 |
| `distance-two` | 14,554,691 | +6,600,709 | 4.737 | 4.281 | 152,092 / 149,876 |

Same-input baseline archives (bytes) · XZ 9 extreme 16,711,344 · Zstandard 19 19,356,133 · Zstandard 3 20,188,613

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#place-distances)

### arc-distances · 21,155,400 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `distance-all` | 4,242,861 | +16,912,539 | 5.818 | 2.145 | 220,072 / 132,180 |
| `distance-direct` | 19,891,770 | +1,263,630 | 1.149 | 0.941 | 97,036 / 94,688 |
| `distance-rows` | 13,383,793 | +7,771,607 | 1.292 | 1.581 | 140,884 / 124,496 |
| `distance-sphere` | 4,242,861 | +16,912,539 | 3.315 | 2.242 | 164,956 / 131,912 |
| `distance-three` | 14,975,990 | +6,179,410 | 1.762 | 3.083 | 153,468 / 151,524 |

Same-input baseline archives (bytes) · XZ 9 extreme 16,371,240 · Zstandard 19 19,114,392 · Zstandard 3 20,007,568

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#arc-distances)

### random-triangle · 21,155,400 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `distance-all` | 21,155,413 | -13 | 4.823 | 0.769 | 206,032 / 76,064 |
| `distance-direct` | 21,155,413 | -13 | 0.808 | 0.581 | 77,180 / 76,244 |
| `distance-rows` | 21,155,413 | -13 | 0.809 | 0.641 | 140,972 / 76,240 |
| `distance-sphere` | 21,155,413 | -13 | 3.226 | 0.909 | 165,688 / 75,900 |
| `distance-three` | 21,155,413 | -13 | 1.468 | 0.519 | 166,220 / 76,240 |

Same-input baseline archives (bytes) · XZ 9 extreme 21,156,512 · Zstandard 19 21,155,900 · Zstandard 3 21,155,900

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#random-triangle)

### walk-distances · 21,155,400 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) | Peak KiB (encode / decode) |
|---|---:|---:|---:|---:|---:|
| `distance-direct` | 20,725,737 | +429,663 | 1.189 | 0.662 | 97,520 / 96,060 |
| `distance-joint` | 2,860,313 | +18,295,087 | 4.178 | 2.658 | 184,104 / 125,408 |
| `distance-rows` | 10,164,974 | +10,990,426 | 1.299 | 0.967 | 141,704 / 118,100 |
| `distance-three` | 2,860,313 | +18,295,087 | 2.572 | 3.109 | 143,732 / 125,760 |
| `distance-two` | 2,925,332 | +18,230,068 | 2.121 | 2.414 | 142,972 / 126,984 |

Same-input baseline archives (bytes) · XZ 9 extreme 17,954,172 · Zstandard 19 19,976,964 · Zstandard 3 20,717,883

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#walk-distances)

<!-- END generated project measurements -->

## Connections

This tests one specific nonrectangular geometry. Compare [lattice prediction](../lattice-prediction/README.md), which searches rectangular lags on the same byte stream.
