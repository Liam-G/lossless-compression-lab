# Whiteboard quotients inside factor trees

## Question and prior work

The [original whiteboard](whiteboard.png) represents an integer as a ratio of repeated-digit numbers in different bases. Write a repdigit as `G(b,r,c) = c (b^r − 1)/(b − 1)`. QBT1 can describe a tree leaf as `p × (G(b,r,c) / G(d,t,e))` when the inner quotient is integral. A missing denominator means one. A second experiment asks whether extracting a factor before choosing the next split can expose a quotient that a split of the original integer misses.

The QBT1 encoder and decoder come from `lab/hutter/ragc/entropy_base_tree/big_tree.py`. Its modular filters discard candidates cheaply before exact integer and width checks. It tries the root, binary splits, several asymmetric root cuts and selected deeper paths anchored at the beginning, middle and end. The new FWF1 search is in [factor_forest.py](factor_forest.py). The separate fourth-power construction lives in [quartic trees](../quartic-trees/README.md).

## Run the experiment

```sh
mkdir -p runs
python3 research/whiteboard-trees/tree.py decode research/whiteboard-trees/original-control.qbt runs/whiteboard.bin
python3 research/whiteboard-trees/tree.py bench "$Q" runs/big-whiteboard
cmp research/whiteboard-trees/original-control.qbt runs/big-whiteboard/planted-big.qbt
python3 research/whiteboard-trees/benchmark_forest.py "$CORPUS" runs/forest
python3 research/whiteboard-trees/factor_forest.py encode runs/whiteboard.bin runs/example.fwf --profile nested
python3 research/whiteboard-trees/factor_forest.py decode runs/example.fwf runs/forest.bin
cmp runs/whiteboard.bin runs/forest.bin
```

## Variants and format

QBT1 stores the byte length in a 12-byte header. Each node selects a literal, a centered split, an explicit unequal cut or a formula with seven integer parameters. The decoder derives each child's width from its parent. The 33-byte planted archive consists of the header, one split and two formulas. The new encoder reproduced the [historical archive](original-control.qbt) byte for byte. On full Q the encoder selected a literal root, yielding 96,994,200 bytes. [Full-Q and planted replay](results/big-results.json)

FWF1 starts from 64-byte words, permits three levels and up to two factor nodes on a path. The encoder can apply `n = p × child − δ`, with δ in {0, +1, −1}, then split the child's bits. It tries up to two exact divisors per correction from ten small primes. Literal and leading-zero-trimmed leaves, bisecting splits and a common width rule are shared across profiles. The encoder chooses by the byte length of the actual tagged records.

## Inputs, results and interpretation

| 32 KiB hidden-product control | Archive bytes |
|---|---:|
| Literal leaves and splits | 30,577 |
| Factors and splits | 29,528 |
| Whiteboard leaves and splits | 30,577 |
| Factors restricted to an unsplit leaf | 29,434 |
| Nested factors, splits and formulas | 21,597 |
| Zstandard level 3 | 18,723 |

The fixture embeds a cross-base quotient in one half of a cofactor, then applies a small prime and a possible one-unit correction. Decoding counted 507 quotient leaves below factors and 457 splits below factors. The nested method saved 7,837 bytes over restricting factors to leaves. Zstandard compressed this same control further. On the real MR, X-ray and spreadsheet slices all five profiles tied. This bounded search establishes where operator order matters and gives its cost on data without the plant. [Every profile, input hash and decoded node count](results/forest/trials.csv)
