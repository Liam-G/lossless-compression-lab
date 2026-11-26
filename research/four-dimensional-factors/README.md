# Four-dimensional automata with noisy binary matrix factors

## Question and prior work

Can inverse evolution recover approximate low rank after motion in four axes? Can equally valid bases yield different coded lengths?

### Source files and compatibility

This extends the U/V/E constructions from local reports 028–031, the predecessor search in report 013, and numbered experiments 06–08. F4D1 is a new format with a small native panel factorizer and a separate forward inverse.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/four-dimensional-factors/control.py runs/spacetime.bin
python3 research/four-dimensional-factors/codec.py encode runs/spacetime.bin runs/spacetime.f4d --profile joint
python3 research/four-dimensional-factors/codec.py decode runs/spacetime.f4d runs/spacetime.restored
cmp runs/spacetime.bin runs/spacetime.restored
```

## Variants and format

Each 64 KiB volume has open time, z, y and packed x axes. Each axis has two parity updates. Linear neighbor-XOR and nonlinear two-neighbor rules have an exact inverse obtained by reversing the schedule. Independently, each 16×8 panel stores two basis rows, two coordinate bit masks and its exact XOR residual. Six binary changes of basis preserve the product. The joint mode ranks predecessor samples and fully prices two candidate factorizations plus the step-zero factorization. Stored bases and coordinates are sufficient to decode.

## Inputs and measurement

The 24 MiB plant has slowly changing bases, independently sampled coordinates and a deliberate one-bit error in every other panel. Each volume then evolves a chosen number of steps. The real numerical and Samba inputs and uniform bytes use exactly the same search.

## Results

On the plant, direct and equivalent-factor profiles gave 25,120,549 bytes. The orbit alone gave 19,601,212. Combining inverse evolution with factor/residual coding gave 9,414,787. On real numerical data the joint profile tied the orbit-only result of 16,013,206. Samba and uniform data also showed no incremental factor gain. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `noisy-spacetime` (25,165,824 raw bytes), `four-joint` produced 9,414,787 archive bytes. [Input and timing](../large-scale/results/by-dataset.md#noisy-spacetime) · [All project measurements](../large-scale/results/by-experiment.md#four-dimensional-factors)

## Connections

The [three-dimensional exact rank study](../tensor-orbits/README.md) uses different panels. The [motion residual study](../motion-residuals/README.md) works on natural sequences of luminance frames.
