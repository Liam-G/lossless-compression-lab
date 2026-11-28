# Recursive fourth-power quotients

> **Verdict: loses on real data.** Best real input: Q: the record archive as an integer, 2.6× larger vs zstd -19.
>
> Part of [chapter 1](../../report/1-formulas.md) of the [report](../../report/README.md). Terms: [glossary](../../report/glossary.md).

## Question

Can Q be written as nested formulas of the form (a⁴ + d⁴) / 2ᵏ, recursing into a and d?

## How it works

```mermaid
flowchart LR
    I["Whole-file integer"] --> T["Decompose recursively into fourth-power operands"]
    T --> W["Write subtree references or explicit operands"]
```

Each node solves for two operands whose fourth powers produce the target, then recurses into the operands until they are small.

<details><summary>Technical details</summary>

How long is a whole-file formula when its operands also have to be specified? The original GMP engine in `lab/hutter/divisors/q-torri-quoziente/ricorsiva/quartiche.cpp` constructs nodes of the form `F(k,a,d) = floor((a⁴ + d⁴) / 2ᵏ)`. The decoder knows how to derive the shift and child widths. The encoder uses integer fourth roots and remainders to construct both children and continues recursively. Small subtrees use a shared 65,536-entry dictionary whose terminal operands are the integers 0 through 15.

**Mechanism and test.** An exact formula can lengthen an archive when each operand requires another description. The fresh full-Q and Wikipedia runs measure how much the recursive operands cost at file scale.

The historical engine accepted the integer width separately. The QW01 wrapper stores the original byte count and significant bit width in a 20-byte header, preserving empty input and leading zero bytes. The original engine supplies the remaining bytes. Each recursive reference or explicitly encoded pair of child descriptions contributes to the formula length.

</details>

## Results on 20 MiB inputs

Every archive below decoded byte-exact. *Our archive* is this project's own format. *Our transform → standard tool* reshapes the bytes reversibly and hands the result to gzip, zstd or xz; it is listed only where it beats that same tool on the raw bytes. *Best standard tool* is the smallest of gzip, bzip2, xz, Zstandard, Brotli and PPMd (plus domain codecs for images, scans and video) on the raw bytes. *Difference* compares the better of our two columns with it; negative = ours is smaller.

| Input | Kind | Raw bytes | Our archive | Our transform → standard tool | Best standard tool | Difference |
|---|---|---:|---:|---:|---:|---:|
| Wikipedia text, another 24 MiB | real | 25,165,824 | 69,926,330 (`quartic`) | — | 6,637,336 (xz -9e) | 10.5× larger |
| Q: the record archive as an integer | derived from real | 96,994,187 | 247,891,575 (`quartic`) | — | 96,994,649 (zstd -19) | 2.6× larger |

<details><summary>All profiles, timings and entropy measurements</summary>

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. *Bytes saved* is raw size minus archive (and any reference the decoder needs). Timings are one run on a shared desktop.

These tables list every measured profile. The comparison with the best standard tool on each input (gzip, bzip2, xz, Zstandard, Brotli, PPMd and the domain codecs) is the Results table above.

### Archive comparison across inputs

![Delivered size by profile and input, expressed as a percentage of the original. Exact bytes follow in the tables.](figures/archives.svg)

Read down a column to compare methods on identical input. Lower is better. 100% is the raw file size. Where available, standard codecs appear below the dividing line. Near 100%, cells give the exact byte difference from raw (+ means larger). Below 0.1%, they give the exact delivered total. A dash means the combination was unmeasured.

This project's published large-file trials measure complete archives. The effect on gzip, Zstandard or XZ after an isolated preprocessing step is unmeasured here.

### wiki-transfer · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `quartic` | 69,926,330 | -44,760,506 | 349.841 | 133.186 |

Same-input baseline archives (bytes) · XZ 9 extreme 6,637,336 · Zstandard 19 6,891,038 · Zstandard 3 8,968,456

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#wiki-transfer)

### cofattore-Q.base256 · 96,994,187 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `quartic` | 247,891,575 | -150,897,388 | 1986.913 | 1309.108 |

Same-input baseline archives (bytes) · XZ 9 extreme 96,998,528 · Zstandard 19 96,994,649 · Zstandard 3 96,996,424

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#cofattore-qbase256)

### Reproduce the large-file comparison

From the repository root, with the pinned inputs and project dependencies installed, replay all published standalone profiles for this folder into a fresh directory.

```sh
python3 research/large-scale/primary.py runs/replay-quartic-trees --project quartic-trees --all-profiles
```

[Dataset preparation](../large-scale/README.md#inputs) · [Archive hashes and settings](../large-scale/results/archives.jsonl)

<!-- END generated project measurements -->

</details>

## Small-scale results

The primary trial measures `quartic` on the complete `wiki-transfer` input (25,165,824 raw bytes). The runner invokes a separate decoder and compares the reconstructed file byte for byte. The earlier measurements below retain their original input sizes.

Fresh Q prefixes of 4 KiB, 64 KiB and 1 MiB produced 11,450, 181,137 and 2,483,741 archive bytes with the wrapper. All decoded exactly. The [historical full-Q measurement](original-full-q.json) recorded 247,891,597 formula bytes before wrapper framing, with 956,890,129 fourth-power nodes when fully expanded and maximum depth 39. It includes matching input and reconstructed SHA-256 digests. A fresh QW01 encode of all 96,994,187 Q bytes produced 247,891,575 archive bytes and passed independent decoding. The receipts preserve each measurement under its own format and build. Both full runs spent more bytes describing the two operands than the original integer occupied. [Prefix replay](../evidence/native-replay/trials.csv)

## Run it

```sh
mkdir -p runs
head -c 4096 "$Q" > runs/q-prefix.bin
python3 research/quartic-trees/codec.py encode runs/q-prefix.bin runs/q.quartic
python3 research/quartic-trees/codec.py decode runs/q.quartic runs/q-prefix.restored
cmp runs/q-prefix.bin runs/q-prefix.restored
python3 research/benchmark_native.py "$Q" runs/native-quartics
```
