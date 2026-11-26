# Measurement protocol

## Archive costs

Experiment 01 reads and writes RPS1. Experiments 02–16 use LCX1. Its fixed prefix contains four magic bytes followed by one byte each for experiment ID and profile index. An unsigned LEB128 field gives the original size, followed by a four-byte big-endian metadata length, the metadata stream and the body. Each experiment defines its records and inverse. Headers, selectors, dictionary definitions, references and literal padding all count toward the measured archive size.

In LCX1, the metadata column measures the common header and the separate metadata stream. Some body codes interleave syntax with coded values. Those bytes are included in archive bytes. The experiment-specific details column reports additional breakdowns such as formula coverage, error-stream sizes or tree paths.

For factorial comparisons, the component gain is the smaller single-component archive minus the combined archive. Positive values favor the combination. A separate comparison subtracts the smallest experiment archive from the original and from the Zstd level-3 archive. In multiway comparisons the best column gives the first tied profile in declared order. A per-file best profile is an observed minimum across the sweep.

## Inputs, timing and correctness

The per-experiment drivers fix search catalogs, seeds and operating points before encoding. The first structured case also supplies the length for an independent uniform control. Real inputs and their provenance ship with the repository. These small research corpora support mechanism tests. Some methods use the same family both to plant a control and to predict it. The real inputs provide a separate check on transfer.

Each trial uses a fresh worker and one monotonic-clock measurement in each direction. Encode time includes model building, search and serialization. Decode time includes reconstructing the original byte string. Process startup, disk I/O and construction of the package are outside both timed regions. Peak RSS is Linux process high-water memory in KiB through verification. Experiment 01 additionally separates catalog construction. Timings and RSS depend on runtime and machine.

Every archived result has passed a full byte comparison, as has the streamed Zstd baseline. Each experiment also has CLI round-trip tests, short and empty inputs, and an isolated test of the delivered decoder. The environment JSON files record source versions and input hashes appear in the CSV files.

## Decoder and reference delivery

Archive bytes assume that both parties have the codec. Bundle bytes measure a stored Python zip application containing the codec, its local runtime modules, the payload and any required reference. A compatible Python interpreter is assumed on the receiving machine. Experiment 15 additionally measures delivery of a single decoder for two complete binaries. Experiment 12 reports both a patch for someone who owns the reference and the raw reference plus patch for a new recipient.

## Reproduction

From the root, run `python3 suite.py test` to exercise all sixteen codecs, or `python3 suite.py benchmark runs/reproduction` to regenerate their measurements in a fresh directory. Each joint study has its own command. Checked-in benchmark tables remain alongside the relevant implementation, with the exact reference environment and raw trial details. CPU-budgeted searches can vary with machine speed. Any selected archive must still reconstruct its input exactly.
