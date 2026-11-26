# Field notes from the original workspace

The long-form technical register, `esperimenti_descrizioni_tecniche.txt`, leads to 149 original reports across the workspace. The [English index](report-index.tsv) gives a stable ID, translated title, original path, size and SHA-256 for each report. Paths are relative to the directory containing the original Italian thesis list. The table below connects the broader work to the implementations in this repository. Historical findings in this table are attributed to their report IDs.

| Report IDs | What was tried | What the measurement established |
|---|---|---|
| 001, 148–149 | Grammar, BWT, chains of transforms, shape discovery and context mixing | A 381-chain screen on 10 MB found a words-plus-BWT transform that improved XZ by 5.7%. The full-enwik8 CM3 archive reached 17,811,463 bytes. The old fax row-neighborhood score motivated the new archive-level test. |
| 004–005, 012–013 | Checkerboard predecessors, orbit seeds, step indices and recursively factorable matrices | A backward step can expose a cheaper factorization. GFH1 verifies this by independently decoding the selected state and reproducing original fixture archives. |
| 022–032 | Division chains, explicit cofactor descriptors, prime exponents, multidimensional U/V/E fields and mixed-arity trees | Neif's 26,734 × 26,736 binary matrix had exact rank 26,733. Introducing an XOR correction allowed smaller factors, but the residual also needed encoding. Historical 3D evolution of U used 13,367 planes of 2 × 4 bits. The backward-only variants gave zero savings against matched step-zero controls. |
| 032, 128, 137 | Factorable neighbors and prime indices | In a 16-bit prime-index search on Q, 6,977,503 words individually selected prime or product coding, yet all 1,481 block comparisons chose the untagged literal alternative. Full-Q sizes in that report came from exact counts. Sample archives were serialized. |
| 065, 009–014 | Whole-file algebra and recursive quartics | An exact expression can be enormous after charging for both operands. The full-Q quartic report gives matching source and reconstructed hashes and counts explicit and shared nodes separately. |
| 015–021, 033–039, 059–064, 119, 142 | Recover executable structure, re-encode model tensor weights and rebuild the cofactor | The original V15 portable package occupies 96,920,967 bytes including its decoders. A fresh decode recovered all of Q, a saving of 73,220 bytes. It exploited file-specific structure in the executable and weights inside 12 × Q. This was a substantially larger real gain than the arithmetic-only trees. |
| 040–058, 066–079 | Order patches, conditional dictionaries, replay packages and arithmetic-stream regeneration | These experiments have different delivery conditions. In particular, the 92,780,256-byte replay package in report 119 had release hashes and a small control. Full Q regeneration from that package remained unverified there. |
| 082–118, 120–126, 138–147 | Causal context models, article history, URL and title prediction, token streams and metadata | The relevant common input can be an internal decoder tape or probability trace. A shorter component must pay for integration into the final stream. Use the indexed native and full-corpus reports to identify the actual target of each result. |
| 119, 127–136 | Generator banks with exact residuals, arithmetic fields, substring transforms and recurrence fits | A generator bank with small corrections produced large savings on its planted sequence. At six correction bytes it found 1,657 matches on Q vs 1,643 on matched random data, and expanded Q by 4,720 bytes after selectors. |
| 140–141 | Exact cross-base ratios and short arithmetic records | The 117-bit integer (2¹²⁰ − 1)/13 has a 22-bit recipe in the original gamma format. Whether a substring pays for a position and width is a separate question, tested by RPS1 and QFT1. |

## How to interpret the replays

The [mixed-tree and quartic replay](native-replay/trials.csv) identifies its input by hash. The full-Q, shape and matrix benchmark pages link their own raw results. Where a fourth-power or context-mixer full-file result was available only in the prior measurements, the project pages label its origin. A formula that generates a planted dataset, a locally useful transform, a portable whole-file package and an estimate from a trace each answer a different compression question.


## Recheck the strongest recorded portable Q package

The local V15 package includes its decoder and the dedicated executable/model representation. Its complete fresh reconstruction was compared with canonical Q. The [replay record](portable-q-v15.json) includes both hashes. The package remains in the source workspace. Starting at the repository root, with the variables from the research index, run the following.

```sh
mkdir -p runs
python3 -S ../lab/hutter/divisors/q-coda-ricerca/qwx8/Q.portatile-v15.pyz decode runs/q-v15.restored
cmp "$Q" runs/q-v15.restored
```
