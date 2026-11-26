# Byte-valued cellular automata and Kronecker factors

## Question and prior work

The local discussion proposed larger cellular alphabets and Kronecker or tensor factors in topics 35 and 38. Can reversing a cellular rule expose a product of two small matrices when its cells carry full byte values? This implementation uses arithmetic modulo 256. The earlier binary, three-dimensional, and four-dimensional experiments are linked below. [Original idea register](../evidence/idea-atlas.md)

## Run the experiment

The codec requires Python, NumPy and python-zstandard. Run from the repository root.

```sh
mkdir -p runs/modular-input
python3 research/modular-kronecker/control.py runs/modular-input/modular-panels
python3 suite.py benchmark runs/modular-result --project modular-kronecker --raw runs/modular-input
python3 research/modular-kronecker/codec.py encode runs/modular-input/modular-panels runs/panels.mkr --profile adaptive-joint
python3 research/modular-kronecker/codec.py decode runs/panels.mkr runs/panels.out
cmp runs/modular-input/modular-panels runs/panels.out
```

## Variants and format

A 16 × 16 periodic byte grid has two checkerboard phases. On each phase a cell adds its north neighbor, its east neighbor and three times its south neighbor modulo 256. The neighbors lie on the other color. Subtracting the same values in reverse phase order exactly inverts the step.

The factor model represents a 16 × 16 grid as two 4 × 4 byte matrices and a byte residual. For outer coordinates i,j and inner coordinates k,l, the predicted cell at (4i+k, 4j+l) equals A[i,j] × B[k,l] modulo 256. An odd pivot is invertible in this ring. The fixed fit uses the top-left pivot. The adaptive fit chooses an odd pivot anywhere in the rearranged grid. Only the actual factors travel in the stream, so the decoder needs no pivot location. The valuation variant strips the power of two common to every cell before inverting a pivot. It retains that scale in the first factor and needs no extra decoder fields. Even when a prediction fails, the stored residual recovers every cell.

Each 256 KiB bank pays for its mode, time, raw size and payload size. The encoder tests 0, 1, 2 and 4 reverse steps and compares whole candidate archives using the same Zstandard level. Literal and direct Zstandard modes are always available. A final partial grid travels verbatim within its bank payload.

## Inputs and measurement

Each generated input has 98,304 grids and exactly **25,165,824 raw bytes**. Every grid receives independently sampled factors and approximately one corrupted cell in 128 before evolution. The first two seeds constrain the top-left pivot to be odd. A third seed removes that condition. A fourth multiplies each noisy bank by 2, 4 or 8 before evolution, making every candidate pivot even. The real numerical corpus and uniform controls use the same encoder. [Seeds and source hashes](../large-scale/synthetic.json)

## Results

On the first seed, factors alone used 25,166,796 bytes and orbit reversal alone used 24,560,134. Combining them used **4,471,016 bytes**, a saving of 20,089,118 over the better component. A second seed yielded 4,480,896 bytes for the joint model and 24,560,992 for the orbit alone. All four fixed-pivot profiles tied at 14,949,292 bytes on the real Silesia numerical stream. Both direct and joint coding used 25,166,796 bytes on the matched uniform input.

Removing the planted odd top-left condition exposed a failure in the fixed normalization. The joint codec grew to 20,947,779 bytes. Choosing an odd pivot separately for each panel reduced it to **5,813,021 bytes** on the identical 25,165,824 bytes. The adaptive factor model alone used 25,166,796 bytes and orbit reversal alone used 24,347,838. On the Graphviz library raster and the original whiteboard cost tables, all the tested adaptive profiles tied their direct coding controls.

On the all-even control, orbit reversal alone and the adaptive odd-pivot joint encoder each used 17,965,503 bytes. Valuation-aware fitting alone used 18,871,144. Combining valuation-aware fitting and orbit reversal reduced the archive to **5,067,269 bytes**.

## Large-file benchmark

On `modular-panels` (25,165,824 raw bytes), `modular-joint` produced 4,471,016 archive bytes. Zstandard level 3 used 25,166,414 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#modular-panels) · [All project measurements](../large-scale/results/by-experiment.md#modular-kronecker)

## Connections

[Binary matrix and orbit models](../tensor-orbits/README.md) · [Four-dimensional binary factors](../four-dimensional-factors/README.md) · [Learning a rule jointly with an error basis](../learned-cellular-rules/README.md)
