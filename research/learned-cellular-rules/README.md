# Jointly learning a cellular rule and the matrix of its prediction errors

## Question and prior work

The original checkerboard and multidimensional automaton searches select a rule from a fixed family before factoring its output. What happens when the rule itself cannot be inferred until the error planes are considered together? This extension learns a 32-entry nonlinear truth table per bit plane and a triangular GF(2) change of basis for the residual byte. It compares independent training with joint training from the same raw frames.

## Run the experiment

```sh
make -C research
python3 research/learned-cellular-rules/control.py runs/large/raw/learned-field
python3 research/large-scale/bench.py runs/large/raw/learned-field runs/learned-cellular.jsonl learned-direct learned-rule learned-basis learned-joint learned-coupled
```

## Variants and format

Each 16-frame bank chooses literal storage, a direct compressed stream, a temporal XOR, or a fitted cellular predictor. Five binary inputs from the preceding frame supply a lookup address for every bit. The inputs are the center cell and its four direct neighbors. A second-order option also XORs the cell from two frames earlier. The first frame is carried as part of the predictive residual. Each rule table costs four bytes per plane.

The triangular matrix has a unit diagonal, so an 8-byte row-mask descriptor suffices for its inverse. In the sequential `joint` profile the encoder fits each transition by majority vote and then fits a basis to its errors. In `coupled`, the encoder learns a plane's truth table conditional on the parity of already modeled error planes. A Walsh–Hadamard transform scores all eligible parities from a small contingency table. A penalty discourages spurious lookup entries in nearly balanced noise. The decoder needs only the selected tables and basis. Both profiles use the same candidate archive format, bit-plane layouts, framing and Zstandard 6.

## Inputs and measurement

The primary control contains eight separately generated banks of sixteen 640 × 360 frames and independent rule tables. Two dense innovation planes mix into six sparse ones. The other controls change the seed, shift each residual bit plane to break cross-plane alignment, or supply uniform noise. Three real grayscale clips use the same geometry and byte count. See the [input manifests](../large-scale/synthetic.json) and [video sources](../large-scale/videos.json).

## Results

On the 29,491,200-byte generated field, fixed-order training followed by a basis produced 25,054,265 bytes. Joint estimation of the rule and basis produced **11,051,733**. On a fresh seed the sequential and coupled archives were 26,700,643 and 11,045,164 bytes. Shifting each error plane independently reduced the coupled advantage to one byte, 25,262,112 versus 25,262,111. Uniform noise tied at 29,491,268. The real clips selected the same archive sizes under the two profiles, including 1,647,841 bytes on Jake and 4,139,127 on Rei. The planted result identifies a dependency the sequential model missed. The real-video measurements put a limit on its observed transfer. [Archives and ablations](../large-scale/results/by-dataset.md#learned-field)


## Large-file benchmark

On `learned-field` (29,491,200 raw bytes), `learned-coupled` produced 11,051,733 archive bytes. [Input and timing](../large-scale/results/by-dataset.md#learned-field) · [All project measurements](../large-scale/results/by-experiment.md#learned-cellular-rules)

## Connections

[Four-dimensional fixed rules](../four-dimensional-factors/README.md) · [Reversible clock search](../checkerboard-orbits/README.md) · [Walsh representation](../../experiments/09-walsh-bitplanes/README.md) · [Motion references](../motion-residuals/README.md)
