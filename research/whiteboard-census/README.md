# The whiteboard census and its formula witnesses

## Question and prior work

The 2019 board proposed the ratio of two repeated-digit integers. How many values actually have a cheap representation, and do those same equations help compress the research outputs? This project restores `lab/whiteboard/rep_fast.c`, the independent Python brute-force checker and the original analysis of every recorded saving witness. The census tables, witness archives and ordinary raw files are three different targets.

## Run the experiment

```sh
make -C research
mkdir -p runs/census
research/build/whiteboard-census 12 14 runs/census/small > runs/census/small.json
python3 research/whiteboard-census/brute_check.py 12 14 runs/census/small.f6.u8 runs/census/small.f3.u8 runs/census/check.json r1closed
python3 research/whiteboard-census/data.py .. runs/large/raw
python3 research/whiteboard-census/genuine.py runs/large/raw/nonunit-witnesses
python3 research/large-scale/replay.py whiteboard-witnesses runs/replay-witness witness-joint
python3 research/large-scale/replay.py whiteboard-costs runs/replay-census census-exact censusapp-source
```

## Variants and format

For each positive integer below 2ᴺ, F3 records the minimum sum of the bit lengths of a digit, base and exponent. F6 records the analogous minimum for a ratio of two such triples, subject to a total budget K. A value of 255 marks a missing admissible ratio. The native enumerator prunes impossible magnitude pairs and tests surviving divisions using exact 64-bit or GMP arithmetic. The checker independently builds small cases with Python integers. The historical N=24 run found 142,040 apparent savers at the sum-of-bit-lengths price. Only 171 survived its separately specified gamma price. [Historical source map](../evidence/idea-atlas.md)

WCT1 compares general compression with a one-digit prediction, a lower-budget census plus XOR residuals, and a full matching census. WFW1 reads the original packed little-endian witness records. It can separate their fields, or evaluate the numerator and denominator from three or six parameters and predict the integer and its bit-length cost. The combined version also prices column differences, stores any arithmetic mismatch exactly and removes the predictable base offset when an exponent is one.

## Inputs and measurement

The **33,554,432-byte** cost target is the concatenation of the retained N=24 F3 and F6 files. The **22,630,320-byte** witness target contains two counts and the original N=26 record streams, including every value, parameter, cost and record position. The shuffled control keeps the same parameters and permutes complete value/cost pairs. Every decoder reconstructs the complete target. [Source member hashes](../large-scale/whiteboard.json)

## Results

| Witness representation | Archive bytes |
|---|---:|
| Direct Zstandard with framing | 4,289,180 |
| Separated columns | 2,306,827 |
| Recompute values and costs | 1,600,689 |
| Recompute and code columns | **1,082,142** |

Shuffling value/cost pairs among records reversed the result. Arithmetic alone grew to 5,638,203 bytes, and the joint selector chose the 3,721,398-byte column archive. On the unshuffled records, whole-file XZ extreme used 2,679,352 bytes.

For the cost table, running the census with K=21 and transmitting corrections took 316,324 bytes. K=23 recreated the measured table with a **15-byte descriptor and a shared enumerator**. The package containing both the enumerator's C source and its extraction code used **5,911 bytes**. The source package needs a C compiler and GMP development files. The binary package used 10,528 bytes and requires a compatible Linux ABI and installed GMP. The 387,915-byte variant also delivers GMP. [Complete archive and delivery comparisons](../large-scale/results/by-dataset.md#whiteboard-costs)

The new N=28, K=27 census found 1,515,430 six-parameter records. Filtering on the actual denominator retained 913,077 records whose denominator exceeds one, totaling **32,870,784 raw bytes** with framing. Columns alone cost 5,053,332 bytes, recomputing the arithmetic cost 2,937,903, and combining them cost **2,378,373**. Zstandard level 19 used 6,038,280 bytes. These records come from a separate enumeration of a wider range, which can include values already present in N=26. [Generator and member digests](../large-scale/nonunit.json)

The reduced-budget predictor also benefits from the equation itself. A denominator equal to one costs four parameter bits, so an admissible F3 representation implies an F6 upper bound. Applying that bound reduced the K=21 residual archive from 316,324 to 246,627 bytes. Grouping corrections by byte value and Rice-coding gaps between their positions cost 187,296 bytes on its own. Combining that coding with the arithmetic bound cost **137,209 bytes**, saving 50,087 bytes over the better individual change. All four configurations recover the same original 33,554,432 bytes.

An independent exhaustive Python check agreed on all 4,095 positive integers for N=12, K=14. On this host the generic and CPU-optimized C builds reproduced both historical N=24 cost tables. Several parameter tuples can tie at the same cost. The generic build reproduced the original F3 witness files while the original CPU-native build also reproduced both historical F6 witness files byte for byte at N=24 and N=26. [Exact build comparisons](compatibility.json)

### Shipping the witness computation

A further comparison regenerates the **sequence of records**, including their original order. WRT1 infers the bit width, budget and denominator filter, runs the same enumerator, and stores a SHA-256 digest of its prediction. It also sends the exact remaining differences. On the original N=26 witnesses, the generic build differed at 739 byte positions and used a **2,051-byte archive**. On this host the CPU-native build matched every position and used **48 bytes** with that enumerator installed. Shuffling the values and costs increased the generic archive to 3,589,802 bytes. The newly generated N=28 non-unit subset also regenerated from a 48-byte descriptor with its matching generic enumerator.

WRP1 delivers a Python extractor and the enumerator inside the archive. The source package used **6,068 bytes** including the 48-byte model and decoded the historical 22,630,320-byte stream in 42.7 seconds in this run. It requires Python, a compatible C compiler and GMP headers. The package carrying the CPU-native executable used 11,723 bytes and requires a compatible CPU, Linux ABI and GMP runtime. The generic source package with a DEFLATE correction cost 29,100 bytes. Each extractor checks the predicted sequence before applying corrections. These savings exploit a known computation that generated the target. [Complete delivery and timing receipts](../large-scale/results/by-dataset.md#whiteboard-witnesses)

## Large-file benchmark

On `whiteboard-witnesses` (22,630,320 raw bytes), `witness-joint` produced 1,082,142 archive bytes. Zstandard level 3 used 4,602,358 bytes on the same input. [Input and timing](../large-scale/results/by-dataset.md#whiteboard-witnesses) · [All project measurements](../large-scale/results/by-experiment.md#whiteboard-census)

## Connections

[Whiteboard quotient trees](../whiteboard-trees/README.md) · [Formulas as shared factor-tree leaves](../shared-factor-forest/README.md) · [Prices including the decoder](../portable-arithmetic/README.md)
