# Experiment 07 · Automata and recursive GF(2) factorization

## Question and prior work

Does undoing a reversible transformation before factorization expose low rank, and does a third level of recursion help?

The original GFH1 study reported 8,205 bytes for leaf-only automata versus 4,492 with pre-factorization automata on 256 evolved rank-four matrices.

### Source files and compatibility

The port reuses the original factor, rank, subset, tree serialization and decoding routines. Its Python phase walk replaces the native predecessor search. The ported node decoder also restored the 4,492-byte historical GFH1 archive to its 8,192-byte reference input. Paths below are relative to the original workspace.

- `lab/hutter/divisors/neif-2-condiviso/ricorsivi/esperimenti-per-struttura/gerarchico-gf2/RISULTATI.md`
- `lab/hutter/divisors/neif-2-condiviso/ricorsivi/esperimenti-per-struttura/gerarchico-gf2/gerarchico.py`
- `lab/hutter/divisors/neif-2-condiviso/ricorsivi/esperimenti-per-struttura/gerarchico-gf2/orbita.cpp`

## Run the experiment

Run from this folder on Linux with Python 3.10 or newer and the Zstd CLI. The codec writes new output files. Choose a fresh directory for each benchmark run.

```sh
python3 ../../lab.py 07 test
python3 ../../lab.py 07 encode ../../fixtures/fax-mid.bin sample.lcx
python3 ../../lab.py 07 decode sample.lcx sample.restored
cmp ../../fixtures/fax-mid.bin sample.restored
python3 ../../lab.py 07 benchmark ../../runs/recheck-07
```

## Variants and format

Port the original 16×16 GF(2) row reduction, basis partitions, combinadic ranks and tree-node decoder. A node can emit raw cells, an enumerated mask, or independent row indices and three recursive child matrices. The step index allows a seed matrix to be evolved after reconstruction. The post profiles permit transformation on leaf encodings. Pre additionally tests transformed factorization roots. Cross each with depth one or three. Search four earlier states with beam width two. An outer file flag allows a literal fallback.

The [codec](codec.py) defines the profiles in wire order. Pass a profile name with `encode --profile NAME`. The [benchmark protocol](../../PROTOCOL.md) specifies the common archive header, byte accounting and decoder delivery convention.

## Inputs and measurement

Check matrices evolved by the decoder rule, matrices evolved by a different nonlinear rule, and hierarchical matrices with shared half-rows. Test low and high image bit planes from the frozen fixtures. Every measured archive is included under results/reference/archives. The trial details count decoded node types by depth.

LCX1 wraps the ported node stream. Its small orbit limit and Python search give it a different runtime and framing from the native GFH1 benchmark.

The [benchmark driver](benchmark.py) freezes the corpus construction. The same seeded uniform control has the first planted input's length. Every profile runs once per file in a fresh worker. [Fixture provenance](../../fixtures/README.md).

## Results

On the matched-rule control, permitting the automaton before the split reduced the depth-one archive from 778 to 355 bytes. Depth three tied depth one on that input.

| Input | Raw bytes | Smallest profile (first on ties) | Archive bytes | Zstd bytes |
|---|---:|---|---:|---:|
| matched-rule | 768 | pre-1 | 355 | 781 |
| uniform | 768 | post-1 | 781 | 781 |
| different-rule | 768 | post-1 | 774 | 781 |
| hierarchical | 768 | post-1 | 327 | 653 |
| fax.bin-plane0 | 64 | post-1 | 15 | 21 |
| fax.bin-plane5 | 64 | post-1 | 15 | 21 |
| fax-mid.bin-plane0 | 64 | post-1 | 29 | 37 |
| fax-mid.bin-plane5 | 64 | post-1 | 28 | 41 |
| medical.bin-plane0 | 64 | post-1 | 47 | 52 |
| medical.bin-plane5 | 64 | post-1 | 15 | 21 |

All 40 profile archives decoded byte for byte. The [trial measurements](results/reference/trials.csv) give timings, peak RSS, metadata, bundle bytes and method details. The [full comparison](results/reference/comparison.csv) includes every profile and both baselines. [Environment and source hashes](results/reference/environment.json). [Verified archives](results/reference/archives).

## Connections

Experiment 06 supplies the reversible transformation. Experiment 08 adds a mask for inexact factors.
