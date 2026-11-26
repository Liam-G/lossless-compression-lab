# Hierarchical GF(2) with checkerboard evolution

## Question and prior work

Can backward cellular evolution recover the low rank of a matrix before recursive factorization? GFH1 divides a file into 16 × 16 binary matrices. Its native predecessor search and independent Python decoder are ported from `lab/hutter/divisors/neif-2-condiviso/ricorsivi/esperimenti-per-struttura/gerarchico-gf2/{orbita.cpp,gerarchico.py}`. The ten original inputs and ten corresponding full-profile archives are included as compatibility vectors.

## Run the experiment

```sh
mkdir -p runs
python3 research/hierarchical-gf2/codec.py pack --profile full research/hierarchical-gf2/fixtures/rank-4-evolved.bin runs/matrix.gfh
python3 research/hierarchical-gf2/codec.py unpack runs/matrix.gfh runs/matrix.bin
cmp research/hierarchical-gf2/fixtures/rank-4-evolved.bin runs/matrix.bin
cmp research/hierarchical-gf2/fixtures/rank-4-evolved.gfh runs/matrix.gfh
python3 research/hierarchical-gf2/benchmark.py runs/gf2-replay
```

## Variants and format

The six profiles measure direct coding, automaton alone, a single factorization, recursive factorization, automata at leaves, and the full ordering with predecessor search before factorization. A factor node transmits a rank, a subset of independent row positions and recursively coded factor data. A predecessor carries the forward step count needed for reconstruction. GFH1 can fall back to the original file plus its 13-byte header. The benchmark uses up to 100 steps, depth 3 and a beam of 2 candidates. The previously published pilot explores a smaller search.

## Inputs, results and interpretation

Each input is 8,192 bytes. On the evolved rank-four fixture, all restricted profiles gave 8,205 bytes. The full profile gave 4,492. On the hierarchical fixture, single-level factorization gave 6,471 and recursive factorization gave 5,514. Plain rank-four matrices already reached 4,267 bytes with one factorization. The uniform and Neif payload fixtures selected literal files. All 60 trials matched the original measured sizes, and all ten full-profile encodes reproduced the historical archive bytes exactly. [Replay with decoded node counts](results/replay/trials.csv)
