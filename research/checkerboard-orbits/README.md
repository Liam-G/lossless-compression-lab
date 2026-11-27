# A shared clock for 8 × 8 checkerboard automata

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

## Connections

The [3D](../tensor-orbits/README.md) and [4D](../four-dimensional-factors/README.md) projects use different rules and look for low-rank predecessors. Experiment 06 measures two 2D rule families.

## Inspect one torus

The English port of the workspace's `gioca_automa.py` prints each cell in the recorded grid and compares the minimum-entropy predecessor with the smallest complete packet.

```sh
python3 research/checkerboard-orbits/explore.py --recorded --steps 255 --save runs/recorded.torus
python3 research/checkerboard-orbits/explore.py --open runs/recorded.torus
```

In the archived 8 × 8 crop the lowest entropy occurs at step 183, whereas the smallest packet occurs at step 35. Its bytes are `08 08 23 2c 4e 4e e5 a1 d5 32 5d`. This is a format-compatibility vector. The full corpus measurements use independent large inputs.
