# Distance matrices reconstructed from landmarks

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

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#distance-geometry) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

This tests one specific nonrectangular geometry. Compare [lattice prediction](../lattice-prediction/README.md), which searches rectangular lags on the same byte stream.
