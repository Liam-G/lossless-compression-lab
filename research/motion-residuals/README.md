# Motion and spatial residuals on grayscale frame sequences

## Question and prior work

When consecutive planes are actual frames, does a motion vector improve prediction enough to pay for its two stored coordinates?

### Source files and compatibility

The nested-plane and stride experiments in `lab/shape/nested.py` motivated this transfer to a time axis. MVR1 adds an exact integer motion predictor and tests it against spatial-only and previous-frame baselines.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
python3 research/motion-residuals/codec.py encode runs/large/raw/luma-jake runs/movie.mvr --width 640 --height 360 --profile joint
python3 research/motion-residuals/codec.py decode runs/movie.mvr runs/movie.restored
cmp runs/large/raw/luma-jake runs/movie.restored
```

## Variants and format

The header supplies width, height and frame count. A frame can use literal pixels, spatial differences, the previous frame, or an integral motion vector per 32×32 tile. Coarse-to-fine search picks the vector using subsampled absolute differences. The joint profile can apply a left or median-edge predictor to temporal errors before ZigZag and Zstandard coding. The previous frame, vector field and residual determine the next frame exactly.

## Inputs and measurement

Each source supplies its first 128 frames, scaled once to 640×360 unsigned 8-bit luma. The raw streams are 29,491,200 bytes each. FFV1 and lossless H.264 are compared by decoding back to identical luma bytes. The experiment measures compression of these canonical frames.

## Results

On Jake, spatial-only used 7,865,422 bytes, previous-frame prediction 1,201,348, and the combined codec 1,188,089. Lossless H.264 was smaller at 803,426. On Rei the combined archive gave 3,882,245, again above lossless H.264 (2,666,233). The time axis explained much more than the extra motion search on these clips. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#motion-residuals) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Compare [four-dimensional automata](../four-dimensional-factors/README.md) and [wavelet lifting](../reversible-wavelets/README.md) on static RGB images.
