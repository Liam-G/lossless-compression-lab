# Measurement protocol

The measurement rules now live in the report: **[report/methods.md](report/methods.md)**.

In short: every archive counts all of its bytes, is decoded by a separate process and compared byte for byte
with the input; every method is compared with the best of a fixed panel of standard tools on the same bytes;
real, derived, self-generated and planted inputs are always reported separately.

Container details used by the sixteen numbered experiments: experiment 01 reads and writes RPS1;
experiments 02–16 use LCX1 (4-byte magic, 1-byte experiment ID, 1-byte profile index, LEB128 original size,
4-byte big-endian metadata length, metadata, body). Headers, selectors, dictionaries, references and padding all
count toward the archive size. Run `python3 suite.py test` for round-trip tests of all sixteen codecs.
