# Statico M1 grammar compressor

> **Verdict: loses on real data.** Best real input: Wikipedia text, enwik8 (100 MB), +6.1% vs xz -9e.
>
> On the full enwik8: 26,346,968 B; with GLZA-style rule choice 23,774,125 B ([grammar probes](../grammar-probes/README.md)).
>
> Part of [chapter 5](../../report/5-text.md) of the [report](../../report/README.md). Terms: [glossary](../../report/glossary.md).

## Question

How far does a grammar compressor (repeated strings become numbered rules) get on text and binaries?

## How it works

```mermaid
flowchart LR
    I["Repeated source substrings"] --> T["Construct grammar productions and references"]
    T --> W["Encode definitions and symbol-frequency classes"]
```

A suffix array finds repeated strings, the best become rules (recursively), and the rule numbers are coded by frequency class and index.

<details><summary>Technical details</summary>

How far can an explicit grammar compress ordinary text and binary data? This is the native M1 project from the workspace's `statico/` repository at commit `53e45d8950d0e5f803993c0423d60f1bb2742bb4`. It includes the suffix-array implementation and license, grammar builder, encoder, decoder, range coder, unit and edge-case tests. Its range coder is also used by the factor-tree and spatial experiments.

**Mechanism and test.** A production saves bytes when later references amortize its definition. Short-lived or rare substrings can lose. The corpus results bound that tradeoff for the implemented grammar and cost model.

M1 constructs repeated substrings as grammar productions, emits their definitions inline, then codes symbol frequency classes and indices. STC1 carries the mode and original length. Its compressed modes store a SHA-256 digest. The implementation includes order-zero and stored representations. The decoder reconstructs production bodies and the top-level symbol sequence. The default production cost was used in the replay.

</details>

## Results on 20 MiB inputs

Every archive below decoded byte-exact. *Our archive* is this project's own format. *Our transform → standard tool* reshapes the bytes reversibly and hands the result to gzip, zstd or xz; it is listed only where it beats that same tool on the raw bytes. *Best standard tool* is the smallest of gzip, bzip2, xz, Zstandard, Brotli and PPMd (plus domain codecs for images, scans and video) on the raw bytes. *Difference* compares the better of our two columns with it; negative = ours is smaller.

| Input | Kind | Raw bytes | Our archive | Our transform → standard tool | Best standard tool | Difference |
|---|---|---:|---:|---:|---:|---:|
| Wikipedia text, enwik8 (100 MB) | real | 100,000,000 | 26,346,968 (`statico`) | — | 24,831,648 (xz -9e) | +6.1% |
| Silesia nci (chemical database) | real | 33,553,445 | 1,686,759 (`statico`) | — | 1,449,272 (xz -9e) | +16.4% |
| Silesia numerical files (mr + x-ray + sao) | real | 25,696,748 | 14,428,360 (`statico`) | — | 11,662,476 (xz -9e) | +23.7% |
| Silesia samba (source tarball) | real | 21,606,400 | 4,760,025 (`statico`) | — | 3,739,524 (xz -9e) | +27.3% |
| Wikipedia text, another 24 MiB | real | 25,165,824 | 7,063,035 (`statico`) | — | 6,637,336 (xz -9e) | +6.4% |

<details><summary>All profiles, timings and entropy measurements</summary>

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. *Bytes saved* is raw size minus archive (and any reference the decoder needs). Timings are one run on a shared desktop.

These tables list every measured profile. The comparison with the best standard tool on each input (gzip, bzip2, xz, Zstandard, Brotli, PPMd and the domain codecs) is the Results table above.

### Archive comparison across inputs

![Delivered size by profile and input, expressed as a percentage of the original. Exact bytes follow in the tables.](figures/archives.svg)

Read down a column to compare methods on identical input. Lower is better. 100% is the raw file size. Where available, standard codecs appear below the dividing line. Near 100%, cells give the exact byte difference from raw (+ means larger). Below 0.1%, they give the exact delivered total. A dash means the combination was unmeasured.

This project's published large-file trials measure complete archives. The effect on gzip, Zstandard or XZ after an isolated preprocessing step is unmeasured here.

### enwik8 · 100,000,000 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `statico` | 26,346,968 | +73,653,032 | 861.664 | 13.744 |

Same-input baseline archives (bytes) · XZ 9 extreme 24,831,648 · Zstandard 19 26,944,227 · Zstandard 3 35,445,335

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#enwik8)

### nci · 33,553,445 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `statico` | 1,686,759 | +31,866,686 | 94.449 | 0.703 |

Same-input baseline archives (bytes) · XZ 9 extreme 1,449,272 · Zstandard 19 1,664,988 · Zstandard 3 2,835,400

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#nci)

### numerical · 25,696,748 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `statico` | 14,428,360 | +11,268,388 | 826.119 | 3.637 |

Same-input baseline archives (bytes) · XZ 9 extreme 11,662,476 · Zstandard 19 13,213,336 · Zstandard 3 15,163,683

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#numerical)

### samba · 21,606,400 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `statico` | 4,760,025 | +16,846,375 | 158.272 | 1.063 |

Same-input baseline archives (bytes) · XZ 9 extreme 3,739,524 · Zstandard 19 3,894,675 · Zstandard 3 4,957,768

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#samba)

### wiki-transfer · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `statico` | 7,063,035 | +18,102,789 | 156.269 | 1.250 |

Same-input baseline archives (bytes) · XZ 9 extreme 6,637,336 · Zstandard 19 6,891,038 · Zstandard 3 8,968,456

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#wiki-transfer)

### Reproduce the large-file comparison

From the repository root, with the pinned inputs and project dependencies installed, replay all published standalone profiles for this folder into a fresh directory.

```sh
python3 research/large-scale/primary.py runs/replay-statico --project statico --all-profiles
```

[Dataset preparation](../large-scale/README.md#inputs) · [Archive hashes and settings](../large-scale/results/archives.jsonl)

<!-- END generated project measurements -->

</details>

## Small-scale results

The primary trial measures `statico` on the complete `enwik8` input (100,000,000 raw bytes). The runner invokes a separate decoder and compares the reconstructed file byte for byte. The earlier measurements below retain their original input sizes.

Silesia osdb (10,085,684 bytes) encoded to 2,723,344. Silesia dickens (10,192,446 bytes) encoded to 2,780,136. Both full reconstructions matched their input hashes and the original archive lengths. The historical enwik8 result was 26,346,968 bytes. Its grammar contained 553,204 rules. The full Silesia table shows where this approach lost ground, including mozilla and x-ray. [Fresh full-file results](bench/results/replay.json) · [Historical benchmark and XZ settings](bench/results/README.md)

## Run it

```sh
mkdir -p runs
make -C research/statico -j2 test
research/statico/statico c research/statico/tests/data/sample.txt runs/grammar.stc
research/statico/unstatico runs/grammar.stc runs/grammar.restored
cmp research/statico/tests/data/sample.txt runs/grammar.restored
python3 research/statico/bench/bench.py "$CORPUS/silesia/osdb" "$CORPUS/silesia/dickens" --out runs/statico.json
```
