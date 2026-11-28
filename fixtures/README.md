# Benchmark fixtures

Small frozen inputs used by the round-trip tests of the sixteen numbered experiments (`python3 suite.py test`). They are test vectors, not benchmark results: real comparisons use inputs of at least 20 MiB ([methods](../report/methods.md)). Paths below refer to the public corpora (`corpus/`) or to files of the original lab notebook (`lab/`), which is not part of this repository.

| File | Bytes | Origin |
|---|---:|---|
| fax.bin | 512 | Bytes 40000 through 40511 of `corpus/canterbury/ptt5` |
| medical.bin | 512 | Bytes 123456 through 123967 of `corpus/silesia/mr` |
| integer.bin | 512 | Bytes 131072 through 131583 of `lab/hutter/divisors/work/cofattore-Q.base256` |
| rusage.elf | 16,584 | Unmodified `lab/baselines/rusage_exec`, loaded as bytes |
| scanner.elf | 23,128 | Unmodified `lab/hutter/ragc/repdigit_split/scan`, loaded as bytes |
| grammar-fd90565.txt | 776 | From 256 bytes before the W.swap call through the available suffix (up to 1,024 further bytes), statico revision `fd90565`, src/grammar.cpp |
| grammar-1061fc7.txt | 967 | From 256 bytes before the W.swap call through the available suffix (up to 1,024 further bytes), statico revision `1061fc7`, src/grammar.cpp |
| logo-old.png | 1,563 | Debian logo PNG from an Ubuntu 20.04 (focal) root filesystem |
| logo-new.png | 1,678 | Debian logo PNG from a Debian 12 (bookworm) root filesystem |
| identifiers-grammar.txt | 768 | First 64 lowercase alphanumeric identifiers/words of length 3–12 in `statico/src/grammar.cpp`, right-padded with 0 to 12 characters |
| identifiers-codec.txt | 768 | First 64 lowercase alphanumeric identifiers/words of length 3–12 in `statico/src/glz.hpp`, right-padded with 0 to 12 characters |
| affine-0.bin | 512 | Signed 16-bit normalized operands of instructions 1–128 in the original formula.bin stream |
| affine-1.bin | 512 | Signed 16-bit normalized operands of instructions 129–256 in the original formula.bin stream |
| bytecode-bwt.bin | 512 | First 512 concatenated function bytecode bytes from `lab/arena/coincidence_bwt.py`, compiled with Python 3.14.10 |
| bytecode-base.bin | 512 | First 512 concatenated function bytecode bytes from `lab/hutter/ragc/entropy_base_tree/trial.py`, compiled with Python 3.14.10 |
| fax-mid.bin | 512 | Midpoint window at offset 256608 in Canterbury ptt5, accompanying the blank window at offset 40000 |
