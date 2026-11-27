# Conditional patches after arithmetic alignment

[View this project's benchmark tables](#large-file-benchmark)

## Question and prior work

Can a cheap arithmetic transformation turn a reference into a useful predictor, and what does the result cost when the receiver must also obtain the reference?

### Source files and compatibility

Reports 021, 057 and 058 distinguish a shared model, a reference patch and computational reproduction. ARF1 is a new, general archive with a content-addressed reference. It also tests the older lab observation that the matching FX2 numerator is exactly 3,072 times Q.

## Run the experiment

Run these commands from the repository root. The [large-suite instructions](../large-scale/README.md) give input preparation, dependencies and the complete benchmark command.

```sh
mkdir -p runs
BASE=../lab/hutter/divisors/fx2-cmix-transformer-archive9.bin
python3 research/arithmetic-references/codec.py encode "$Q" runs/q.arf --reference "$BASE" --profile exact
python3 research/arithmetic-references/codec.py decode runs/q.arf runs/q-relative.restored --reference "$BASE"
cmp "$Q" runs/q-relative.restored
```

## Variants and format

The encoder compares direct Zstandard 9, Zstandard patch-from, and an XOR delta after multiplying or dividing the entire reference integer. Dispersed exact-byte probes shortlist scales. The exact profile can omit the residual when the prediction is identical. The header carries the target width, mode, scale and required reference SHA-256. Direct mode can decode without a base.

## Inputs and measurement

The complete award release and the exact original FX2 numerator are separate references for Q. Two independent transfers use the decompressed package tar streams of adjacent NumPy and Mesa releases. The measurements identify both hashes and show base delivery separately.

## Results

The matching 96,994,188-byte numerator and a 46-byte formula recover all of Q; delivering both costs 96,994,234 bytes. With the other FX2 award release the exact profile selected direct coding at 96,996,466. The NumPy update used 1,347,467 bytes relative to its older package, versus 10,201,056 direct. Mesa also benefited from a conventional patch. [Full archive sizes, times and hashes](../large-scale/results/by-dataset.md)


## Large-file benchmark

On `numpy-update` (53,800,960 raw bytes), `relative-joint` produced 1,347,467 archive bytes. Delivering the required reference as well costs 55,066,507 bytes. Zstandard level 3 used 11,502,762 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#numpy-update) · [All project measurements](../large-scale/results/by-experiment.md#arithmetic-references)

<!-- BEGIN generated project measurements -->

Each archive passed a byte-for-byte round trip. Bytes saved subtracts the archive and any required reference from the raw input size. Timings are seconds from one run.

### numpy-update · 53,800,960 raw bytes

**Standalone archives**

| Profile | Archive bytes | Archive + required reference (bytes) | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|---:|
| `relative-direct` (base `numpy-base`) | 10,201,056 | 10,201,056 | +43,599,904 | 8.960 | 2.061 |
| `relative-joint` (base `numpy-base`) | 1,347,467 | 55,066,507 | -1,265,547 | 60.708 | 2.311 |
| `relative-numeric` (base `numpy-base`) | 10,201,056 | 10,201,056 | +43,599,904 | 43.941 | 1.944 |
| `relative-patch` (base `numpy-base`) | 1,347,467 | 55,066,507 | -1,265,547 | 9.894 | 2.551 |

Same-input baseline archives (bytes) · XZ 9 extreme 8,272,288 · Zstandard 19 9,104,011 · Zstandard 3 11,502,762

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#numpy-update)

### cofattore-Q.base256 · 96,994,187 raw bytes

**Standalone archives**

| Profile | Archive bytes | Archive + required reference (bytes) | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|---:|
| `relative-direct` (base `fx2-cmix-t-awarded.archive9`) | 96,996,466 | 96,996,466 | -2,279 | 1.987 | 2.407 |
| `relative-exact` (base `fx2-cmix-t-awarded.archive9`) | 96,996,466 | 96,996,466 | -2,279 | 45.158 | 2.573 |
| `relative-exact` (base `fx2-cmix-transformer-archive9.bin`) | 46 | 96,994,234 | -47 | 29.909 | 3.724 |
| `relative-joint` (base `fx2-cmix-t-awarded.archive9`) | 96,996,466 | 96,996,466 | -2,279 | 63.236 | 2.786 |
| `relative-joint` (base `fx2-cmix-transformer-archive9.bin`) | 3,028 | 96,997,216 | -3,029 | 59.035 | 5.324 |
| `relative-numeric` (base `fx2-cmix-t-awarded.archive9`) | 96,996,466 | 96,996,466 | -2,279 | 39.524 | 2.994 |
| `relative-numeric` (base `fx2-cmix-transformer-archive9.bin`) | 3,028 | 96,997,216 | -3,029 | 35.276 | 7.237 |
| `relative-patch` (base `fx2-cmix-t-awarded.archive9`) | 96,996,466 | 96,996,466 | -2,279 | 6.263 | 3.166 |
| `relative-patch` (base `fx2-cmix-transformer-archive9.bin`) | 96,996,466 | 96,996,466 | -2,279 | 8.375 | 2.642 |

Same-input baseline archives (bytes) · XZ 9 extreme 96,998,528 · Zstandard 19 96,994,649 · Zstandard 3 96,996,424

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#cofattore-qbase256)

### mesa-update · 67,133,440 raw bytes

**Standalone archives**

| Profile | Archive bytes | Archive + required reference (bytes) | Bytes saved vs raw | Encode (s) | Decode (s) |
|---|---:|---:|---:|---:|---:|
| `relative-direct` (base `mesa-base`) | 19,832,536 | 19,832,536 | +47,300,904 | 12.167 | 2.646 |
| `relative-joint` (base `mesa-base`) | 13,146,431 | 79,307,071 | -12,173,631 | 53.086 | 2.310 |
| `relative-numeric` (base `mesa-base`) | 19,832,536 | 19,832,536 | +47,300,904 | 34.607 | 2.094 |
| `relative-patch` (base `mesa-base`) | 13,146,431 | 79,307,071 | -12,173,631 | 19.326 | 3.453 |

Same-input baseline archives (bytes) · XZ 9 extreme 16,198,184 · Zstandard 19 17,697,935 · Zstandard 3 21,668,962

[Input hash and all measured codecs](../large-scale/results/by-dataset.md#mesa-update)

<!-- END generated project measurements -->

## Connections

Experiment 12 uses local copies. [Scale-and-region coding](../carry-trees/README.md) seeks arithmetic structure without an external reference.
