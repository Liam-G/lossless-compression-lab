# Prime ordinal and product coding

[View this project's benchmark tables](#large-file-benchmark)

## Question and prior work

Do savings on many individual prime or factorable words survive the selectors needed for the whole file?

### Source files and compatibility

This is a port of `lab/hutter/divisors/q-fattori-ricorsivi/indici.cpp`. QPI1 uses the original range coder. Report 137 also describes a distinct 16-bit prime-index grammar and is indexed separately.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
research/build/prime-indices tree "$Q" runs/q.qpi
research/build/prime-indices decode runs/q.qpi runs/q-primes.restored
cmp "$Q" runs/q-primes.restored
```

## Variants and format

Fixed, tree and exploratory profiles partition a source word, transmit the model choice, and use prime ordinals when the chosen grammar permits it. A fourth profile uses prime sums on 2-byte units. Small prime tables are deterministically rebuilt by the decoder. The mode and lengths of both arithmetic streams are in the archive.

## Inputs and measurement

The test includes all 96,994,187 bytes of canonical Q and a separate 24 MiB uniform control. Source and archive hashes identify the tested release.

## Results

The four whole-Q archives were 97,005,287 (fixed), 97,006,292 (tree), 98,625,024 (exploratory) and 104,419,953 bytes (sums). On this source the fixed representation came closest to raw size. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `cofattore-Q.base256` (96,994,187 raw bytes), `prime-tree` produced 97,006,292 archive bytes. Zstandard level 3 used 96,996,424 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#cofattore-qbase256) · [All project measurements](../large-scale/results/by-experiment.md#prime-index-trees)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

### cofattore-Q.base256 · 96,994,187 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `prime-explore` | 98,625,024 | -1,630,837 | 30.739 | 9.643 |
| `prime-fixed` | 97,005,287 | -11,100 | 14.531 | 10.304 |
| `prime-sums` | 104,419,953 | -7,425,766 | 12.284 | 9.355 |
| `prime-tree` | 97,006,292 | -12,105 | 23.746 | 9.904 |

Same-input baseline archives (bytes) · XZ 9 extreme 96,998,528 · Zstandard 19 96,994,649 · Zstandard 3 96,996,424

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#cofattore-qbase256)

### uniform · 25,165,824 raw bytes

**Standalone archives**

| Profile | Archive bytes | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|
| `prime-fixed` | 25,168,750 | -2,926 | 3.099 | 1.869 |
| `prime-sums` | 27,092,567 | -1,926,743 | 5.314 | 3.472 |

Same-input baseline archives (bytes) · XZ 9 extreme 25,167,136 · Zstandard 19 25,166,414 · Zstandard 3 25,166,414

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#uniform)

<!-- END generated project measurements -->

## Connections

Compare with [direct factor splitting](../factor-trees/README.md), [shared formulas](../shared-factor-forest/README.md), and report 137 in the [historical register](../evidence/report-index.tsv).
