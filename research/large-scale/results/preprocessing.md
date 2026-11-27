# Preprocessing before standard compression

19 measured input/profile pairs on 14 distinct inputs. Each raw input is at least 20 MiB. Each pair uses exactly the same source bytes on both paths.

1. Compress the original input directly with gzip, Zstandard or XZ.
2. Serialize the reversible preprocessing output, including headers, choices, lengths, dictionaries, model parameters, literal fallbacks and residuals. Measure this stream before backend compression, then compress it with the same executable and settings as the original.
3. Decompress both paths and compare every byte. An independent invocation of the inverse preprocessor must also recover the original input exactly.

## Empirical entropy before and after preprocessing

**H0** is the entropy of the observed byte histogram. **H1** is the entropy of the next byte given the immediately preceding byte, weighted by observed adjacent pairs. Both are in bits per byte of their own stream. The first byte has no predecessor. **Post H0 per input byte** multiplies post H0 by prepared length / original length, so a shorter representation with higher byte entropy can still score well. These are empirical coding estimates for two simple models.

| Input | Preprocessor | Original bytes | Prepared bytes | H0 before → after | H1 before → after | Post H0 per input byte |
|---|---|---:|---:|---:|---:|---:|
| affine-pairs | pilot10-conditional | 25,165,824 | 15,979,518 | 3.7941 → 4.8886 | 2.3861 → 3.4200 | 3.1041 |
| affine-pairs | pilot10-fixed | 25,165,824 | 6,304,526 | 3.7941 → 7.9116 | 2.3861 → 7.8929 | 1.9820 |
| formula-text | pilot11-dag | 25,165,824 | 9,357,678 | 3.6110 → 4.7847 | 1.1528 → 1.7253 | 1.7791 |
| hidden-products | shared-shared | 25,165,824 | 13,379,724 | 6.3745 → 7.9279 | 4.3616 → 7.7994 | 4.2150 |
| learned-field | learned-coupled | 29,491,200 | 29,491,588 | 7.9931 → 3.5692 | 7.9890 → 2.7951 | 3.5693 |
| luma-jake | learned-coupled | 29,491,200 | 29,491,324 | 6.0905 → 1.1219 | 2.2173 → 0.4218 | 1.1219 |
| manual-graphs | pilot07-pre-1 | 24,642,792 | 3,112,119 | 0.7646 → 6.8702 | 0.5291 → 5.9196 | 0.8676 |
| modular-panels | modular-joint | 25,165,824 | 28,312,524 | 7.9918 → 1.6383 | 7.9873 → 1.2147 | 1.8432 |
| noisy-spacetime | four-joint | 25,165,824 | 34,605,324 | 7.9645 → 3.2005 | 7.9554 → 2.0327 | 4.4010 |
| numerical | lattice-joint | 25,696,748 | 25,696,985 | 6.3494 → 4.9333 | 5.5271 → 3.7053 | 4.9333 |
| numerical | modular-joint | 25,696,748 | 25,697,750 | 6.3494 → 6.3493 | 5.5271 → 5.5270 | 6.3495 |
| shared-orbit-1000 | pilot06-checker-3-fixed | 25,165,824 | 22,274,238 | 6.9648 → 7.7281 | 6.3175 → 7.4767 | 6.8401 |
| shuffled-witnesses | witness-joint | 22,630,320 | 19,790,312 | 2.9495 → 3.0670 | 2.7803 → 1.7457 | 2.6821 |
| uniform | modular-joint | 25,165,824 | 25,166,796 | 8.0000 → 8.0000 | 7.9981 → 7.9981 | 8.0003 |
| whiteboard-witnesses | witness-joint | 22,630,320 | 14,110,128 | 2.9495 → 1.9285 | 2.7803 → 0.7663 | 1.2024 |
| wiki-transfer | pilot01-adaptive-ratios | 25,165,824 | 25,178,126 | 5.0850 → 5.0884 | 3.8807 → 3.8808 | 5.0909 |
| wiki-transfer | pilot01-fixed-direct | 25,165,824 | 25,178,126 | 5.0850 → 5.0884 | 3.8807 → 3.8808 | 5.0909 |
| wiki-transfer | views-bwt | 25,165,824 | 25,165,956 | 5.0850 → 5.0851 | 3.8807 → 2.8011 | 5.0851 |
| wiki-transfer | views-mtf | 25,165,824 | 25,165,956 | 5.0850 → 2.6119 | 3.8807 → 2.3702 | 2.6119 |

## Whole-stream compressor results

Each cell gives **compressed original bytes → compressed prepared bytes (percentage saved)**. Positive percentages mean preprocessing helped that compressor. Every run used one whole-stream invocation with stdin, one thread, the same settings on both paths and no external reference. Both recipients are assumed to have the software. The numbers include standard container framing.

| Input | Preprocessor | Zstandard 3 | gzip 6 | XZ 6 |
|---|---|---:|---:|---:|
| affine-pairs | pilot10-conditional | 9,297,291 → 9,175,295 (+1.312%) | 9,973,948 → 9,032,831 (+9.436%) | 6,866,512 → 7,840,772 (-14.189%) |
| affine-pairs | pilot10-fixed | 9,297,291 → 6,304,683 (+32.188%) | 9,973,948 → 6,245,010 (+37.387%) | 6,866,512 → 6,304,896 (+8.179%) |
| formula-text | pilot11-dag | 4,118,040 → 2,187,854 (+46.871%) | 2,958,719 → 2,322,775 (+21.494%) | 1,856,404 → 1,625,172 (+12.456%) |
| hidden-products | shared-shared | 14,343,986 → 13,038,675 (+9.100%) | 14,118,577 → 13,077,821 (+7.372%) | 13,314,968 → 13,011,616 (+2.278%) |
| learned-field | learned-coupled | 29,389,440 → 11,276,527 (+61.631%) | 29,358,227 → 11,231,282 (+61.744%) | 29,419,328 → 10,497,028 (+64.319%) |
| luma-jake | learned-coupled | 1,716,540 → 1,796,738 (-4.672%) | 8,869,318 → 1,712,131 (+80.696%) | 990,504 → 1,375,752 (-38.894%) |
| manual-graphs | pilot07-pre-1 | 1,325,130 → 2,215,382 (-67.182%) | 1,520,849 → 2,217,323 (-45.795%) | 1,004,072 → 2,156,664 (-114.792%) |
| modular-panels | modular-joint | 25,166,413 → 4,478,573 (+82.204%) | 25,168,569 → 4,695,964 (+81.342%) | 25,167,132 → 4,327,872 (+82.803%) |
| noisy-spacetime | four-joint | 25,166,413 → 9,397,974 (+62.657%) | 25,042,968 → 9,362,367 (+62.615%) | 25,063,412 → 8,109,204 (+67.645%) |
| numerical | lattice-joint | 15,163,679 → 11,635,203 (+23.269%) | 15,063,439 → 11,486,297 (+23.747%) | 11,665,916 → 10,449,384 (+10.428%) |
| numerical | modular-joint | 15,163,679 → 15,164,986 (-0.009%) | 15,063,439 → 15,063,384 (+0.000%) | 11,665,916 → 11,730,228 (-0.551%) |
| shared-orbit-1000 | pilot06-checker-3-fixed | 21,987,747 → 21,474,587 (+2.334%) | 22,067,549 → 21,470,554 (+2.705%) | 20,184,408 → 20,716,428 (-2.636%) |
| shuffled-witnesses | witness-joint | 6,474,999 → 3,768,334 (+41.802%) | 6,460,681 → 3,776,913 (+41.540%) | 4,322,840 → 3,550,292 (+17.871%) |
| uniform | modular-joint | 25,166,413 → 25,167,385 (-0.004%) | 25,169,682 → 25,170,654 (-0.004%) | 25,167,136 → 25,168,108 (-0.004%) |
| whiteboard-witnesses | witness-joint | 4,602,354 → 1,109,554 (+75.892%) | 5,230,942 → 1,122,203 (+78.547%) | 2,968,412 → 961,108 (+67.622%) |
| wiki-transfer | pilot01-adaptive-ratios | 8,968,455 → 8,973,354 (-0.055%) | 9,232,082 → 9,246,045 (-0.151%) | 6,743,812 → 6,747,788 (-0.059%) |
| wiki-transfer | pilot01-fixed-direct | 8,968,455 → 8,973,349 (-0.055%) | 9,232,082 → 9,246,040 (-0.151%) | 6,743,812 → 6,747,580 (-0.056%) |
| wiki-transfer | views-bwt | 8,968,455 → 8,800,771 (+1.870%) | 9,232,082 → 8,513,896 (+7.779%) | 6,743,812 → 7,360,740 (-9.148%) |
| wiki-transfer | views-mtf | 8,968,455 → 8,662,902 (+3.407%) | 9,232,082 → 8,627,926 (+6.544%) | 6,743,812 → 7,409,368 (-9.869%) |

## Reproduction

From the repository root, with the pinned inputs prepared and the research binaries built, run:

```sh
mkdir -p runs/paired
python3 research/large-scale/entropy_bench.py lattice-joint runs/large/raw/numerical runs/paired/lattice.json
python3 research/large-scale/preprocess.py prepare lattice-joint runs/large/raw/numerical runs/paired/numerical.pre
python3 research/large-scale/preprocess.py restore runs/paired/numerical.pre runs/paired/numerical.out
cmp runs/large/raw/numerical runs/paired/numerical.out
```

The numbered pilots here already emit a reversible record stream. For the native formats in this study the adapter retains the encoder’s actual block choices, removes each terminal Zstandard frame, and updates its length. On restore it rebuilds those frames for the existing decoder. All backends receive the same frozen representation, including the modes selected by the original encoder’s internal cost model. These observations cover the listed profiles and inputs.

The [machine-readable receipts](preprocessing.jsonl) give the complete input, prepared and compressed stream hashes, commands, versions and byte counts. The [corpus manifest and preparation instructions](../README.md#inputs) describe their provenance.
