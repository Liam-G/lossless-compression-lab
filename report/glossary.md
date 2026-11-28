# Glossary

Words and abbreviations used in this repository, in alphabetical order.

| Term | Meaning |
|---|---|
| **Archive** | The complete compressed file. Every size in this repository counts the whole archive, including headers, parameters, tables, corrections and padding. |
| **Arithmetic coding** | A way to turn a sequence of probabilities into bits. A symbol predicted with probability *p* costs about −log₂ *p* bits. Every strong compressor here ends with one. |
| **Automaton (cellular)** | A grid of cells updated in steps by a fixed local rule (for example "new cell = left XOR right"). *Reversible* automata can be run backwards exactly. |
| **Baseline panel** | The standard tools measured on every input: gzip -9, bzip2 -9, xz -9e, zstd -19 --long, brotli -11 and PPMd order 10. See [methods](methods.md#the-baseline-panel). |
| **bpc / bits per byte** | Compressed bits divided by original bytes. 8.0 means no compression; enwik8 at 1.43 bpc is 17.8 MB. |
| **BWT** | Burrows–Wheeler transform. A reversible reordering of the bytes that groups similar contexts together (used by bzip2). |
| **Carried over** | A number measured earlier in this project with a verified round trip, kept with its original log, not rerun for this report. |
| **cmix, paq8px, nncp** | The strongest published general compressors on text. They are context mixers or neural networks. Their numbers here are *published*, not measured. |
| **CM, CM2, CM3** | Our three generations of context-mixing compressor ([chapter 5](5-text.md)). CM3 is the strongest thing in this repository. |
| **Context mixing** | Many small models each predict the next bit; a learned mixer combines their predictions; an arithmetic coder writes the result. |
| **Control** | An input built to test a claim. *Planted*: data deliberately generated with the structure a method looks for (the method should win). *Shuffled* or *uniform*: the same bytes with the structure destroyed (the method should not win). |
| **Corpus** | A standard set of test files: **enwik8** (first 100 MB of an English Wikipedia dump), **enwik9** (first 1 GB), **Silesia** (12 mixed files, 212 MB), **Canterbury** (11 small files). |
| **Counting argument** | There are 2ⁿ files of *n* bits but fewer than 2ⁿ shorter descriptions, so no method shrinks most files. A search over *G* candidate rules can "find" about log₂ *G* bits by luck, and naming the winning rule costs those same log₂ *G* bits. [Chapter 1](1-formulas.md#why-it-fails-the-counting-argument). |
| **Delivered size** | Archive plus anything else the receiver must be sent to decode it (a reference file, a dictionary, sometimes the decoder program). |
| **Detector test** | A run on planted data. A success shows that the method *can find* the structure it was built for. It says nothing about how often real files have that structure. |
| **Entropy (H0, H1)** | H0: the bits per byte a coder would need using only byte frequencies. H1: the same, given the previous byte. Rough guides only; the real test is the archive size. |
| **enwik8 / enwik9** | See *corpus*. The Hutter Prize is judged on enwik9; this report tests on enwik8 (10× smaller, same kind of text). |
| **Factor tree** | Writing a big integer as a product of factors and recursing into them, keeping the widths needed to rebuild the bytes. |
| **GF(2)** | Arithmetic on bits where 1 + 1 = 0 (addition is XOR). *GF(2) factorization* writes a bit matrix as a product of two smaller bit matrices plus an error matrix. |
| **Grammar compression** | Replace repeated strings with rule numbers, recursively (Statico, GLZA). |
| **Hutter Prize** | A prize for compressing enwik9; the score counts the archive plus the decompressor. The record when this work started was 100,424,672 bytes (fx2-cmix-transformer). |
| **Kronecker product** | A way to build a big matrix from two small ones; a reversible orbit can hide one. |
| **LSTM** | A small recurrent neural network; CM3 uses one as an extra predictor. |
| **LTCB** | The Large Text Compression Benchmark, the public table of enwik8/enwik9 results. Source of all *published* numbers. |
| **Neif** | `cmix-neif 2.0`, a 2026 enwik9 entry whose 89,346,392-byte self-extracting archive is studied in [chapter 6](6-record-archive.md). |
| **Orbit** | The sequence of states an automaton passes through. "Reversing the orbit" means running it backwards to an earlier, simpler state. |
| **PPMd** | Prediction by partial matching, a strong classic text compressor (in 7-Zip). |
| **Published** | A third-party number copied from a public table with its link, not measured here. |
| **Q** | The Hutter-record archive file (`fx2-cmix-transformer` archive9, 96,996,198 bytes) read as one big integer and divided by 3,072. Canonical Q is 96,994,187 bytes. [Chapter 6](6-record-archive.md). |
| **Re-verified** | Measured again for this report (November 28–29, 2026), with a byte-for-byte round trip. |
| **Repdigit** | A number made of one repeated digit in some base, like 7777 in base 10 or 1111 in base 2. The original whiteboard idea divides one repdigit by another. |
| **Residual / correction** | What a model gets wrong, stored exactly so decoding is lossless (for example the positions of wrong bits). |
| **Round trip** | Encode, decode, compare every byte with the original. Every archive size in this report passed one. |
| **Statico** | Our grammar compressor (`research/statico`), the project's first product. |
| **Wire formats** | Short tags for our archive layouts: LCX1 (common container of experiments 02–16), RPS1 (experiment 01), GFH1 (hierarchical GF(2)), QRT (factor trees), QPI1 (prime-index trees), SFF1 (shared factor forest), WCT1/WFW1 (whiteboard census and witnesses), QFT1 (repdigit quotient trees), QHY (hybrid Q packages). |
