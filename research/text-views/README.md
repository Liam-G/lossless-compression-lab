# Text fields, BWT and move-to-front

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

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#text-views) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

Experiment 13 tests generators after BWT. [Statico](../statico/README.md) uses a grammar, and [CM3](../context-mixer/README.md) directly forecasts the original bytes.
