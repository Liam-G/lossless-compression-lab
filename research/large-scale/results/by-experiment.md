# Measurements by experiment

Compare the original input (raw bytes) with the complete encoded file (archive bytes). Bytes saved equals the raw size minus the archive and any required reference. Positive values mean compression. Negative values mean expansion. Projects that use a reference also show the total if the receiver needs that reference delivered. Shared decoder software is excluded. Select an input for same-file baselines and timings.

For entropy before and after preprocessing and matched standard-compressor comparisons, see the [paired preprocessing study](preprocessing.md).

<a id="01-repdigit-segmentation"></a>
## Experiment 01 · Repdigit ratios and adaptive segmentation

[Implementation and protocol](../../../experiments/01-repdigit-segmentation/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| wiki-transfer | pilot01-adaptive-ratios | 5.0850 → 5.0884 | 3.8807 → 3.8808 | 8,968,455 → 8,973,354 |
| wiki-transfer | pilot01-fixed-direct | 5.0850 → 5.0884 | 3.8807 → 3.8808 | 8,968,455 → 8,973,349 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot01-adaptive-ratios | 25,165,824 | 25,178,126 | -12,302 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot01-fixed-direct | 25,165,824 | 25,178,126 | -12,302 |

<a id="02-near-factorization"></a>
## Experiment 02 · Near-factorization and digit concatenation

[Implementation and protocol](../../../experiments/02-near-factorization/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot02-first-exact | 25,165,824 | 26,751,758 | -1,585,934 |

<a id="03-generator-residuals"></a>
## Experiment 03 · Powers, generator sums and exact residuals

[Implementation and protocol](../../../experiments/03-generator-residuals/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot03-power-add-8 | 25,165,824 | 26,751,758 | -1,585,934 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot03-sum-add-8 | 25,165,824 | 26,751,758 | -1,585,934 |

<a id="04-irrational-checkpoints"></a>
## Experiment 04 · Irrational sums, backtracking and checkpoints

[Implementation and protocol](../../../experiments/04-irrational-checkpoints/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot04-10-2-signed-checkpoints | 25,165,824 | 27,248,340 | -2,082,516 |

<a id="05-local-bases"></a>
## Experiment 05 · Local bases and exceptional digits

[Implementation and protocol](../../../experiments/05-local-bases/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [manual-graphs](by-dataset.md#manual-graphs) | pilot05-local-bytes | 24,642,792 | 8,312,441 | +16,330,351 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | pilot05-local-bytes | 33,554,432 | 17,808,940 | +15,745,492 |
| [wiki-dev](by-dataset.md#wiki-dev) | pilot05-local-bytes | 25,165,824 | 26,744,147 | -1,578,323 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot05-local-bytes | 25,165,824 | 26,747,076 | -1,581,252 |

<a id="06-reversible-automata"></a>
## Experiment 06 · Reversible automata and step counts

[Implementation and protocol](../../../experiments/06-reversible-automata/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| shared-orbit-1000 | pilot06-checker-3-fixed | 6.9648 → 7.7281 | 6.3175 → 7.4767 | 21,987,747 → 21,474,587 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [shared-orbit-1000](by-dataset.md#shared-orbit-1000) | pilot06-checker-3-fixed | 25,165,824 | 22,274,238 | +2,891,586 |
| [shared-orbit-1000](by-dataset.md#shared-orbit-1000) | pilot06-zero | 25,165,824 | 25,076,546 | +89,278 |

<a id="07-recursive-gf2"></a>
## Experiment 07 · Automata and recursive GF(2) factorization

[Implementation and protocol](../../../experiments/07-recursive-gf2/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| manual-graphs | pilot07-pre-1 | 0.7646 → 6.8702 | 0.5291 → 5.9196 | 1,325,130 → 2,215,382 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [manual-graphs](by-dataset.md#manual-graphs) | pilot07-pre-1 | 24,642,792 | 3,112,119 | +21,530,673 |

<a id="08-equivalent-factors"></a>
## Experiment 08 · Equivalent matrix factors and error masks

[Implementation and protocol](../../../experiments/08-equivalent-factors/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [numerical](by-dataset.md#numerical) | pilot08-search | 25,696,748 | 24,565,555 | +1,131,193 |

<a id="09-walsh-bitplanes"></a>
## Experiment 09 · Walsh–Hadamard prediction and bit planes

[Implementation and protocol](../../../experiments/09-walsh-bitplanes/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [manual-graphs](by-dataset.md#manual-graphs) | pilot09-combined | 24,642,792 | 12,936,974 | +11,705,818 |
| [manual-graphs](by-dataset.md#manual-graphs) | pilot09-direct | 24,642,792 | 12,437,412 | +12,205,380 |
| [manual-library](by-dataset.md#manual-library) | pilot09-combined | 24,283,584 | 13,922,627 | +10,360,957 |

<a id="10-affine-chains"></a>
## Experiment 10 · Affine instruction chains

[Implementation and protocol](../../../experiments/10-affine-chains/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| affine-pairs | pilot10-conditional | 3.7941 → 4.8886 | 2.3861 → 3.4200 | 9,297,291 → 9,175,295 |
| affine-pairs | pilot10-fixed | 3.7941 → 7.9116 | 2.3861 → 7.8929 | 9,297,291 → 6,304,683 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [affine-pairs](by-dataset.md#affine-pairs) | pilot10-conditional | 25,165,824 | 15,979,518 | +9,186,306 |
| [affine-pairs](by-dataset.md#affine-pairs) | pilot10-dictionary | 25,165,824 | 15,534,921 | +9,630,903 |
| [affine-pairs](by-dataset.md#affine-pairs) | pilot10-fixed | 25,165,824 | 6,304,526 | +18,861,298 |

<a id="11-shared-subexpressions"></a>
## Experiment 11 · Grammars and shared subexpressions

[Implementation and protocol](../../../experiments/11-shared-subexpressions/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| formula-text | pilot11-dag | 3.6110 → 4.7847 | 1.1528 → 1.7253 | 4,118,040 → 2,187,854 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [formula-text](by-dataset.md#formula-text) | pilot11-dag | 25,165,824 | 9,357,678 | +15,808,146 |
| [formula-text](by-dataset.md#formula-text) | pilot11-flat | 25,165,824 | 25,179,662 | -13,838 |

<a id="12-relative-patches"></a>
## Experiment 12 · Relative compression

[Implementation and protocol](../../../experiments/12-relative-patches/README.md)

| Input | Profile | Raw bytes | Archive bytes | Archive + required reference (bytes) | Bytes saved |
|---|---|---:|---:|---:|---:|
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot12-copies (wiki-dev) | 25,165,824 | 15,112,062 | 40,277,886 | -15,112,062 |

<a id="13-bwt-prediction"></a>
## Experiment 13 · Burrows–Wheeler transform and prediction

[Implementation and protocol](../../../experiments/13-bwt-prediction/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [wiki-dev](by-dataset.md#wiki-dev) | pilot13-bwt-64 | 25,165,824 | 27,549,525 | -2,383,701 |
| [wiki-dev](by-dataset.md#wiki-dev) | pilot13-combined-64 | 25,165,824 | 27,942,709 | -2,776,885 |
| [wiki-dev](by-dataset.md#wiki-dev) | pilot13-direct-64 | 25,165,824 | 26,350,492 | -1,184,668 |
| [wiki-dev](by-dataset.md#wiki-dev) | pilot13-predict-64 | 25,165,824 | 26,743,690 | -1,577,866 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot13-combined-64 | 25,165,824 | 27,922,396 | -2,756,572 |

<a id="14-sparse-residuals"></a>
## Experiment 14 · Sparse residual coding

[Implementation and protocol](../../../experiments/14-sparse-residuals/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [numerical](by-dataset.md#numerical) | pilot14-adaptive | 25,696,748 | 20,503,460 | +5,193,288 |

<a id="15-binary-regions"></a>
## Experiment 15 · Regenerating binary regions

[Implementation and protocol](../../../experiments/15-binary-regions/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [mozilla](by-dataset.md#mozilla) | pilot15-combined | 51,220,480 | 35,313,184 | +15,907,296 |
| [mozilla](by-dataset.md#mozilla) | pilot15-literal | 51,220,480 | 51,247,081 | -26,601 |

<a id="16-joint-selection"></a>
## Experiment 16 · Joint selection of compression methods

[Implementation and protocol](../../../experiments/16-joint-selection/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [manual-library](by-dataset.md#manual-library) | pilot16-fixed | 24,283,584 | 10,520,316 | +13,763,268 |
| [manual-library](by-dataset.md#manual-library) | pilot16-intervals-regions | 24,283,584 | 2,157,752 | +22,125,832 |
| [manual-library](by-dataset.md#manual-library) | pilot16-single | 24,283,584 | 2,157,752 | +22,125,832 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | pilot16-fixed | 25,165,824 | 33,206,752 | -8,040,928 |

<a id="formula-factor-grammar"></a>
## Formula leaves, factors and grammar references

[Implementation and protocol](../../../studies/formula-factor-grammar/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [hidden-products](by-dataset.md#hidden-products) | study17-arithmetic-leaves | 25,165,824 | 30,671,807 | -5,505,983 |
| [hidden-products](by-dataset.md#hidden-products) | study17-combined | 25,165,824 | 20,296,188 | +4,869,636 |
| [hidden-products](by-dataset.md#hidden-products) | study17-literal-leaves | 25,165,824 | 30,671,807 | -5,505,983 |
| [hidden-products](by-dataset.md#hidden-products) | study17-shared-leaves | 25,165,824 | 20,296,188 | +4,869,636 |

<a id="automaton-factor-residual"></a>
## Automata, factors and residual coding

[Implementation and protocol](../../../studies/automaton-factor-residual/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [manual-graphs](by-dataset.md#manual-graphs) | study18-direct-enumerative | 24,642,792 | 14,653,191 | +9,989,601 |
| [manual-graphs](by-dataset.md#manual-graphs) | study18-orbit-enumerative | 24,642,792 | 17,725,221 | +6,917,571 |
| [noisy-spacetime](by-dataset.md#noisy-spacetime) | study18-direct-enumerative | 25,165,824 | 31,450,511 | -6,284,687 |

<a id="reference-formula-intervals"></a>
## Reference copies, local formulas and interval selection

[Implementation and protocol](../../../studies/reference-formula-intervals/README.md)

| Input | Profile | Raw bytes | Archive bytes | Archive + required reference (bytes) | Bytes saved |
|---|---|---:|---:|---:|---:|
| [numpy-update](by-dataset.md#numpy-update) | study19-mixed (numpy-base) | 53,800,960 | 18,553,077 | 72,272,117 | -18,471,157 |

<a id="factor-trees"></a>
## Mixed-arity factor trees

[Implementation and protocol](../../factor-trees/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | qrt-binary | 96,994,187 | 96,994,218 | -31 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | qrt-seeded | 96,994,187 | 96,994,214 | -27 |
| [cofattore-Q.txt](by-dataset.md#cofattore-qtxt) | decimal-1000000 | 233,585,278 | 97,001,941 | +136,583,337 |
| [cofattore-Q.txt](by-dataset.md#cofattore-qtxt) | decimal-64000000 | 233,585,278 | 96,994,346 | +136,590,932 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | qrt-binary | 25,165,824 | 25,165,852 | -28 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | qrt-seeded | 25,165,824 | 25,165,851 | -27 |

<a id="whiteboard-trees"></a>
## Whiteboard quotients inside factor trees

[Implementation and protocol](../../whiteboard-trees/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | whiteboard | 96,994,187 | 96,994,200 | -13 |
| [hidden-products](by-dataset.md#hidden-products) | forest-factor | 25,165,824 | 22,597,654 | +2,568,170 |
| [hidden-products](by-dataset.md#hidden-products) | forest-leaf-factor | 25,165,824 | 22,469,215 | +2,696,609 |
| [hidden-products](by-dataset.md#hidden-products) | forest-literal | 25,165,824 | 23,372,356 | +1,793,468 |
| [hidden-products](by-dataset.md#hidden-products) | forest-nested | 25,165,824 | 16,568,758 | +8,597,066 |
| [hidden-products](by-dataset.md#hidden-products) | forest-whiteboard | 25,165,824 | 23,372,356 | +1,793,468 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | whiteboard | 25,165,824 | 25,165,837 | -13 |

<a id="shared-factor-forest"></a>
## Shared formulas inside a factor tree

[Implementation and protocol](../../shared-factor-forest/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| hidden-products | shared-shared | 6.3745 → 7.9279 | 4.3616 → 7.7994 | 14,343,986 → 13,038,675 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [affine-pairs](by-dataset.md#affine-pairs) | shared-direct | 25,165,824 | 10,160,796 | +15,005,028 |
| [affine-pairs](by-dataset.md#affine-pairs) | shared-factor | 25,165,824 | 9,445,541 | +15,720,283 |
| [affine-pairs](by-dataset.md#affine-pairs) | shared-formula | 25,165,824 | 9,445,541 | +15,720,283 |
| [affine-pairs](by-dataset.md#affine-pairs) | shared-inline | 25,165,824 | 9,445,541 | +15,720,283 |
| [affine-pairs](by-dataset.md#affine-pairs) | shared-shared | 25,165,824 | 9,445,541 | +15,720,283 |
| [hidden-products](by-dataset.md#hidden-products) | shared-direct | 25,165,824 | 14,336,766 | +10,829,058 |
| [hidden-products](by-dataset.md#hidden-products) | shared-factor | 25,165,824 | 14,336,766 | +10,829,058 |
| [hidden-products](by-dataset.md#hidden-products) | shared-formula | 25,165,824 | 14,336,766 | +10,829,058 |
| [hidden-products](by-dataset.md#hidden-products) | shared-inline | 25,165,824 | 13,286,101 | +11,879,723 |
| [hidden-products](by-dataset.md#hidden-products) | shared-shared | 25,165,824 | 13,097,327 | +12,068,497 |
| [numerical](by-dataset.md#numerical) | shared-direct | 25,696,748 | 15,272,238 | +10,424,510 |
| [numerical](by-dataset.md#numerical) | shared-factor | 25,696,748 | 15,271,526 | +10,425,222 |
| [numerical](by-dataset.md#numerical) | shared-formula | 25,696,748 | 15,271,526 | +10,425,222 |
| [numerical](by-dataset.md#numerical) | shared-inline | 25,696,748 | 15,271,526 | +10,425,222 |
| [numerical](by-dataset.md#numerical) | shared-shared | 25,696,748 | 15,271,526 | +10,425,222 |
| [uniform](by-dataset.md#uniform) | shared-direct | 25,165,824 | 25,166,508 | -684 |
| [uniform](by-dataset.md#uniform) | shared-factor | 25,165,824 | 25,166,508 | -684 |
| [uniform](by-dataset.md#uniform) | shared-formula | 25,165,824 | 25,166,508 | -684 |
| [uniform](by-dataset.md#uniform) | shared-inline | 25,165,824 | 25,166,508 | -684 |
| [uniform](by-dataset.md#uniform) | shared-shared | 25,165,824 | 25,166,508 | -684 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | shared-direct | 22,630,320 | 4,499,458 | +18,130,862 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | shared-factor | 22,630,320 | 4,460,659 | +18,169,661 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | shared-inline | 22,630,320 | 4,460,659 | +18,169,661 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | shared-shared | 22,630,320 | 4,460,659 | +18,169,661 |

<a id="carry-trees"></a>
## Integer carries across tree boundaries

[Implementation and protocol](../../carry-trees/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | carry-arithmetic | 96,994,187 | 96,994,223 | -36 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | carry-direct | 96,994,187 | 96,994,223 | -36 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | carry-joint | 96,994,187 | 96,994,223 | -36 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | carry-split | 96,994,187 | 96,994,223 | -36 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | scale-direct | 96,994,187 | 96,994,205 | -18 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | scale-informed | 96,994,187 | 96,990,415 | +3,772 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | scale-joint | 96,994,187 | 96,991,891 | +2,296 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | scale-regions | 96,994,187 | 96,993,475 | +712 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | scale-scale | 96,994,187 | 96,994,205 | -18 |
| [mapped-text](by-dataset.md#mapped-text) | carry-arithmetic | 25,165,824 | 14,436,133 | +10,729,691 |
| [mapped-text](by-dataset.md#mapped-text) | carry-direct | 25,165,824 | 14,436,133 | +10,729,691 |
| [mapped-text](by-dataset.md#mapped-text) | carry-joint | 25,165,824 | 9,869,511 | +15,296,313 |
| [mapped-text](by-dataset.md#mapped-text) | carry-split | 25,165,824 | 14,295,184 | +10,870,640 |
| [neif-archive9](by-dataset.md#neif-archive9) | carry-arithmetic | 89,346,392 | 89,346,426 | -34 |
| [neif-archive9](by-dataset.md#neif-archive9) | carry-direct | 89,346,392 | 89,346,426 | -34 |
| [neif-archive9](by-dataset.md#neif-archive9) | carry-joint | 89,346,392 | 89,346,426 | -34 |
| [neif-archive9](by-dataset.md#neif-archive9) | carry-split | 89,346,392 | 89,346,426 | -34 |
| [neif-archive9](by-dataset.md#neif-archive9) | scale-direct | 89,346,392 | 89,346,410 | -18 |
| [neif-archive9](by-dataset.md#neif-archive9) | scale-joint | 89,346,392 | 89,346,307 | +85 |
| [neif-archive9](by-dataset.md#neif-archive9) | scale-regions | 89,346,392 | 89,346,307 | +85 |
| [numerical](by-dataset.md#numerical) | carry-arithmetic | 25,696,748 | 14,355,119 | +11,341,629 |
| [numerical](by-dataset.md#numerical) | carry-direct | 25,696,748 | 15,175,129 | +10,521,619 |
| [numerical](by-dataset.md#numerical) | carry-joint | 25,696,748 | 13,992,442 | +11,704,306 |
| [numerical](by-dataset.md#numerical) | carry-split | 25,696,748 | 15,117,918 | +10,578,830 |
| [uniform](by-dataset.md#uniform) | carry-arithmetic | 25,165,824 | 25,165,842 | -18 |
| [uniform](by-dataset.md#uniform) | carry-direct | 25,165,824 | 25,165,842 | -18 |
| [uniform](by-dataset.md#uniform) | carry-joint | 25,165,824 | 25,165,842 | -18 |
| [uniform](by-dataset.md#uniform) | carry-split | 25,165,824 | 25,165,842 | -18 |
| [uniform](by-dataset.md#uniform) | scale-joint | 25,165,824 | 25,165,842 | -18 |

<a id="prime-index-trees"></a>
## Prime ordinal and product coding

[Implementation and protocol](../../prime-index-trees/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | prime-explore | 96,994,187 | 98,625,024 | -1,630,837 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | prime-fixed | 96,994,187 | 97,005,287 | -11,100 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | prime-sums | 96,994,187 | 104,419,953 | -7,425,766 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | prime-tree | 96,994,187 | 97,006,292 | -12,105 |
| [uniform](by-dataset.md#uniform) | prime-fixed | 25,165,824 | 25,168,750 | -2,926 |
| [uniform](by-dataset.md#uniform) | prime-sums | 25,165,824 | 27,092,567 | -1,926,743 |

<a id="integer-formulas"></a>
## Whole-file square, product and modular-square formulas

[Implementation and protocol](../../integer-formulas/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | integer-composite | 96,994,187 | 96,994,051 | +136 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | integer-floor | 96,994,187 | 96,994,288 | -101 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | integer-mixed | 96,994,187 | 96,994,272 | -85 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | integer-modular | 96,994,187 | 96,994,197 | -10 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | integer-nearest | 96,994,187 | 96,994,277 | -90 |
| [manual-library](by-dataset.md#manual-library) | integer-composite-adjusted | 24,283,584 | 24,283,599 | -15 |
| [manual-library](by-dataset.md#manual-library) | integer-modular-adjusted | 24,283,584 | 24,209,213 | +74,371 |
| [uniform](by-dataset.md#uniform) | integer-composite-adjusted | 25,165,824 | 25,165,841 | -17 |
| [uniform](by-dataset.md#uniform) | integer-modular-adjusted | 25,165,824 | 25,165,838 | -14 |

<a id="generator-sums"></a>
## Three seeded generators plus a signed residual

[Implementation and protocol](../../generator-sums/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | sum-0 | 96,994,187 | 96,994,205 | -18 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | sum-4096 | 96,994,187 | 97,021,897 | -27,710 |
| [numerical](by-dataset.md#numerical) | sum-0 | 25,696,748 | 25,696,765 | -17 |
| [numerical](by-dataset.md#numerical) | sum-4096 | 25,696,748 | 25,708,646 | -11,898 |
| [three-seeds](by-dataset.md#three-seeds) | sum-0 | 25,165,824 | 25,161,749 | +4,075 |
| [three-seeds](by-dataset.md#three-seeds) | sum-4096 | 25,165,824 | 36,872 | +25,128,952 |
| [uniform](by-dataset.md#uniform) | sum-0 | 25,165,824 | 25,165,841 | -17 |
| [uniform](by-dataset.md#uniform) | sum-4096 | 25,165,824 | 25,173,018 | -7,194 |

<a id="whiteboard-census"></a>
## The whiteboard census and its formula witnesses

[Implementation and protocol](../../whiteboard-census/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| shuffled-witnesses | witness-joint | 2.9495 → 3.0670 | 2.7803 → 1.7457 | 6,474,999 → 3,768,334 |
| whiteboard-witnesses | witness-joint | 2.9495 → 1.9285 | 2.7803 → 0.7663 | 4,602,354 → 1,109,554 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [nonunit-witnesses](by-dataset.md#nonunit-witnesses) | regenerate-generic | 32,870,784 | 48 | +32,870,736 |
| [nonunit-witnesses](by-dataset.md#nonunit-witnesses) | witness-arithmetic | 32,870,784 | 2,937,903 | +29,932,881 |
| [nonunit-witnesses](by-dataset.md#nonunit-witnesses) | witness-columns | 32,870,784 | 5,053,332 | +27,817,452 |
| [nonunit-witnesses](by-dataset.md#nonunit-witnesses) | witness-joint | 32,870,784 | 2,378,373 | +30,492,411 |
| [shuffled-witnesses](by-dataset.md#shuffled-witnesses) | regenerate-generic | 22,630,320 | 3,589,802 | +19,040,518 |
| [shuffled-witnesses](by-dataset.md#shuffled-witnesses) | witness-arithmetic | 22,630,320 | 5,638,203 | +16,992,117 |
| [shuffled-witnesses](by-dataset.md#shuffled-witnesses) | witness-columns | 22,630,320 | 3,721,398 | +18,908,922 |
| [shuffled-witnesses](by-dataset.md#shuffled-witnesses) | witness-joint | 22,630,320 | 3,721,398 | +18,908,922 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | census-analytic | 33,554,432 | 3,039,880 | +30,514,552 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | census-direct | 33,554,432 | 3,041,773 | +30,512,659 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | census-events | 33,554,432 | 137,209 | +33,417,223 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | census-exact | 33,554,432 | 15 | +33,554,417 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | census-gaps | 33,554,432 | 187,296 | +33,367,136 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | census-inferred | 33,554,432 | 246,627 | +33,307,805 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | census-narrow | 33,554,432 | 316,324 | +33,238,108 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | censusapp-binary | 33,554,432 | 10,528 | +33,543,904 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | censusapp-gmp | 33,554,432 | 387,915 | +33,166,517 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | censusapp-source | 33,554,432 | 5,911 | +33,548,521 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | regenerate-generic | 22,630,320 | 2,051 | +22,628,269 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | regenerate-native | 22,630,320 | 48 | +22,630,272 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | witness-arithmetic | 22,630,320 | 1,600,689 | +21,029,631 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | witness-columns | 22,630,320 | 2,306,827 | +20,323,493 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | witness-direct | 22,630,320 | 4,289,180 | +18,341,140 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | witness-joint | 22,630,320 | 1,082,142 | +21,548,178 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | witnessapp-binary | 22,630,320 | 11,723 | +22,618,597 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | witnessapp-generic | 22,630,320 | 29,100 | +22,601,220 |
| [whiteboard-witnesses](by-dataset.md#whiteboard-witnesses) | witnessapp-source | 22,630,320 | 6,068 | +22,624,252 |

<a id="portable-arithmetic"></a>
## Arithmetic packages that include their decoder

[Implementation and protocol](../../portable-arithmetic/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | portable-informed | 96,994,187 | 96,992,503 | +1,684 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | portable-joint | 96,994,187 | 96,993,979 | +208 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | portable-literal | 96,994,187 | 96,994,804 | -617 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | portable-standard | 96,994,187 | 96,994,804 | -617 |
| [mapped-text](by-dataset.md#mapped-text) | portable-joint | 25,165,824 | 11,823,400 | +13,342,424 |
| [mapped-text](by-dataset.md#mapped-text) | portable-literal | 25,165,824 | 25,166,441 | -617 |
| [mapped-text](by-dataset.md#mapped-text) | portable-standard | 25,165,824 | 11,823,400 | +13,342,424 |
| [uniform](by-dataset.md#uniform) | portable-informed | 25,165,824 | 25,166,441 | -617 |
| [uniform](by-dataset.md#uniform) | portable-standard | 25,165,824 | 25,166,441 | -617 |

<a id="repdigit-intervals"></a>
## Adaptive repdigit intervals

[Implementation and protocol](../../repdigit-intervals/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | qft255 | 96,994,187 | 96,994,101 | +86 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | rps32 | 96,994,187 | 96,994,108 | +79 |
| [neif-archive9](by-dataset.md#neif-archive9) | qft255 | 89,346,392 | 89,346,365 | +27 |
| [neif-archive9](by-dataset.md#neif-archive9) | rps32 | 89,346,392 | 89,346,365 | +27 |

<a id="quartic-trees"></a>
## Recursive fourth-power quotients

[Implementation and protocol](../../quartic-trees/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | quartic | 96,994,187 | 247,891,575 | -150,897,388 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | quartic | 25,165,824 | 69,926,330 | -44,760,506 |

<a id="hierarchical-gf2"></a>
## Hierarchical GF(2) with checkerboard evolution

[Implementation and protocol](../../hierarchical-gf2/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [manual-graphs](by-dataset.md#manual-graphs) | gfh-3-1 | 24,642,792 | 3,098,408 | +21,544,384 |

<a id="tensor-orbits"></a>
## Reversible 3D automata before GF(2) panel coding

[Implementation and protocol](../../tensor-orbits/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [evolved-volume](by-dataset.md#evolved-volume) | tensor-combined | 25,165,824 | 9,632,435 | +15,533,389 |
| [evolved-volume](by-dataset.md#evolved-volume) | tensor-direct | 25,165,824 | 24,838,928 | +326,896 |
| [evolved-volume](by-dataset.md#evolved-volume) | tensor-orbit | 25,165,824 | 20,763,341 | +4,402,483 |
| [evolved-volume](by-dataset.md#evolved-volume) | tensor-rank | 25,165,824 | 24,837,235 | +328,589 |
| [nci](by-dataset.md#nci) | tensor-combined | 33,553,445 | 4,690,214 | +28,863,231 |
| [nci](by-dataset.md#nci) | tensor-direct | 33,553,445 | 4,690,214 | +28,863,231 |
| [nci](by-dataset.md#nci) | tensor-orbit | 33,553,445 | 4,690,214 | +28,863,231 |
| [nci](by-dataset.md#nci) | tensor-rank | 33,553,445 | 4,690,214 | +28,863,231 |
| [numerical](by-dataset.md#numerical) | tensor-combined | 25,696,748 | 14,514,489 | +11,182,259 |
| [numerical](by-dataset.md#numerical) | tensor-direct | 25,696,748 | 16,487,419 | +9,209,329 |
| [numerical](by-dataset.md#numerical) | tensor-orbit | 25,696,748 | 16,483,488 | +9,213,260 |
| [numerical](by-dataset.md#numerical) | tensor-rank | 25,696,748 | 14,514,642 | +11,182,106 |
| [samba](by-dataset.md#samba) | tensor-combined | 21,606,400 | 6,853,237 | +14,753,163 |
| [samba](by-dataset.md#samba) | tensor-direct | 21,606,400 | 6,853,254 | +14,753,146 |
| [samba](by-dataset.md#samba) | tensor-orbit | 21,606,400 | 6,853,252 | +14,753,148 |
| [samba](by-dataset.md#samba) | tensor-rank | 21,606,400 | 6,853,239 | +14,753,161 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | tensor-combined | 33,554,432 | 3,090,273 | +30,464,159 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | tensor-direct | 33,554,432 | 3,090,273 | +30,464,159 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | tensor-orbit | 33,554,432 | 3,090,273 | +30,464,159 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | tensor-rank | 33,554,432 | 3,090,273 | +30,464,159 |

<a id="checkerboard-orbits"></a>
## A shared clock for 8 × 8 checkerboard automata

[Implementation and protocol](../../checkerboard-orbits/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [numerical](by-dataset.md#numerical) | checker-direct | 25,696,748 | 15,272,238 | +10,424,510 |
| [numerical](by-dataset.md#numerical) | checker-individual | 25,696,748 | 15,272,238 | +10,424,510 |
| [numerical](by-dataset.md#numerical) | checker-joint | 25,696,748 | 15,272,238 | +10,424,510 |
| [numerical](by-dataset.md#numerical) | checker-shared | 25,696,748 | 15,272,238 | +10,424,510 |
| [shared-orbit-1000](by-dataset.md#shared-orbit-1000) | checker-direct | 25,165,824 | 21,999,209 | +3,166,615 |
| [shared-orbit-1000](by-dataset.md#shared-orbit-1000) | checker-individual | 25,165,824 | 13,612,025 | +11,553,799 |
| [shared-orbit-1000](by-dataset.md#shared-orbit-1000) | checker-joint | 25,165,824 | 12,415,836 | +12,749,988 |
| [shared-orbit-1000](by-dataset.md#shared-orbit-1000) | checker-shared | 25,165,824 | 12,415,836 | +12,749,988 |
| [uniform](by-dataset.md#uniform) | checker-direct | 25,165,824 | 25,166,508 | -684 |
| [uniform](by-dataset.md#uniform) | checker-individual | 25,165,824 | 25,166,508 | -684 |
| [uniform](by-dataset.md#uniform) | checker-joint | 25,165,824 | 25,166,508 | -684 |
| [uniform](by-dataset.md#uniform) | checker-shared | 25,165,824 | 25,166,508 | -684 |

<a id="modular-kronecker"></a>
## Byte-valued cellular automata and Kronecker factors

[Implementation and protocol](../../modular-kronecker/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| modular-panels | modular-joint | 7.9918 → 1.6383 | 7.9873 → 1.2147 | 25,166,413 → 4,478,573 |
| numerical | modular-joint | 6.3494 → 6.3493 | 5.5271 → 5.5270 | 15,163,679 → 15,164,986 |
| uniform | modular-joint | 8.0000 → 8.0000 | 7.9981 → 7.9981 | 25,166,413 → 25,167,385 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [manual-library](by-dataset.md#manual-library) | modular-adaptive | 24,283,584 | 1,910,515 | +22,373,069 |
| [manual-library](by-dataset.md#manual-library) | modular-adaptive-joint | 24,283,584 | 1,910,515 | +22,373,069 |
| [manual-library](by-dataset.md#manual-library) | modular-direct | 24,283,584 | 1,910,515 | +22,373,069 |
| [manual-library](by-dataset.md#manual-library) | modular-orbit | 24,283,584 | 1,910,515 | +22,373,069 |
| [manual-library](by-dataset.md#manual-library) | modular-valuation-joint | 24,283,584 | 1,910,515 | +22,373,069 |
| [modular-even](by-dataset.md#modular-even) | modular-adaptive-joint | 25,165,824 | 17,965,503 | +7,200,321 |
| [modular-even](by-dataset.md#modular-even) | modular-direct | 25,165,824 | 18,871,144 | +6,294,680 |
| [modular-even](by-dataset.md#modular-even) | modular-orbit | 25,165,824 | 17,965,503 | +7,200,321 |
| [modular-even](by-dataset.md#modular-even) | modular-valuation | 25,165,824 | 18,871,144 | +6,294,680 |
| [modular-even](by-dataset.md#modular-even) | modular-valuation-joint | 25,165,824 | 5,067,269 | +20,098,555 |
| [modular-free](by-dataset.md#modular-free) | modular-adaptive | 25,165,824 | 25,166,796 | -972 |
| [modular-free](by-dataset.md#modular-free) | modular-adaptive-joint | 25,165,824 | 5,813,021 | +19,352,803 |
| [modular-free](by-dataset.md#modular-free) | modular-direct | 25,165,824 | 25,166,796 | -972 |
| [modular-free](by-dataset.md#modular-free) | modular-factor | 25,165,824 | 25,166,796 | -972 |
| [modular-free](by-dataset.md#modular-free) | modular-joint | 25,165,824 | 20,947,779 | +4,218,045 |
| [modular-free](by-dataset.md#modular-free) | modular-orbit | 25,165,824 | 24,347,838 | +817,986 |
| [modular-panels](by-dataset.md#modular-panels) | modular-direct | 25,165,824 | 25,166,796 | -972 |
| [modular-panels](by-dataset.md#modular-panels) | modular-factor | 25,165,824 | 25,166,796 | -972 |
| [modular-panels](by-dataset.md#modular-panels) | modular-joint | 25,165,824 | 4,471,016 | +20,694,808 |
| [modular-panels](by-dataset.md#modular-panels) | modular-orbit | 25,165,824 | 24,560,134 | +605,690 |
| [modular-transfer](by-dataset.md#modular-transfer) | modular-factor | 25,165,824 | 25,166,796 | -972 |
| [modular-transfer](by-dataset.md#modular-transfer) | modular-joint | 25,165,824 | 4,480,896 | +20,684,928 |
| [modular-transfer](by-dataset.md#modular-transfer) | modular-orbit | 25,165,824 | 24,560,992 | +604,832 |
| [numerical](by-dataset.md#numerical) | modular-direct | 25,696,748 | 14,949,292 | +10,747,456 |
| [numerical](by-dataset.md#numerical) | modular-factor | 25,696,748 | 14,949,292 | +10,747,456 |
| [numerical](by-dataset.md#numerical) | modular-joint | 25,696,748 | 14,949,292 | +10,747,456 |
| [numerical](by-dataset.md#numerical) | modular-orbit | 25,696,748 | 14,949,292 | +10,747,456 |
| [numerical](by-dataset.md#numerical) | modular-valuation-joint | 25,696,748 | 14,949,292 | +10,747,456 |
| [uniform](by-dataset.md#uniform) | modular-direct | 25,165,824 | 25,166,796 | -972 |
| [uniform](by-dataset.md#uniform) | modular-joint | 25,165,824 | 25,166,796 | -972 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | modular-adaptive | 33,554,432 | 3,192,497 | +30,361,935 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | modular-adaptive-joint | 33,554,432 | 3,192,497 | +30,361,935 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | modular-direct | 33,554,432 | 3,192,497 | +30,361,935 |
| [whiteboard-costs](by-dataset.md#whiteboard-costs) | modular-orbit | 33,554,432 | 3,192,497 | +30,361,935 |

<a id="four-dimensional-factors"></a>
## Four-dimensional automata with noisy binary matrix factors

[Implementation and protocol](../../four-dimensional-factors/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| noisy-spacetime | four-joint | 7.9645 → 3.2005 | 7.9554 → 2.0327 | 25,166,413 → 9,397,974 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [noisy-spacetime](by-dataset.md#noisy-spacetime) | four-direct | 25,165,824 | 25,120,549 | +45,275 |
| [noisy-spacetime](by-dataset.md#noisy-spacetime) | four-equivalent | 25,165,824 | 25,120,549 | +45,275 |
| [noisy-spacetime](by-dataset.md#noisy-spacetime) | four-joint | 25,165,824 | 9,414,787 | +15,751,037 |
| [noisy-spacetime](by-dataset.md#noisy-spacetime) | four-orbit | 25,165,824 | 19,601,212 | +5,564,612 |
| [noisy-spacetime](by-dataset.md#noisy-spacetime) | four-rank | 25,165,824 | 25,120,549 | +45,275 |
| [numerical](by-dataset.md#numerical) | four-direct | 25,696,748 | 16,014,181 | +9,682,567 |
| [numerical](by-dataset.md#numerical) | four-equivalent | 25,696,748 | 16,014,181 | +9,682,567 |
| [numerical](by-dataset.md#numerical) | four-joint | 25,696,748 | 16,013,206 | +9,683,542 |
| [numerical](by-dataset.md#numerical) | four-orbit | 25,696,748 | 16,013,206 | +9,683,542 |
| [numerical](by-dataset.md#numerical) | four-rank | 25,696,748 | 16,014,181 | +9,682,567 |
| [samba](by-dataset.md#samba) | four-direct | 21,606,400 | 5,843,228 | +15,763,172 |
| [samba](by-dataset.md#samba) | four-equivalent | 21,606,400 | 5,843,228 | +15,763,172 |
| [samba](by-dataset.md#samba) | four-joint | 21,606,400 | 5,843,228 | +15,763,172 |
| [samba](by-dataset.md#samba) | four-orbit | 21,606,400 | 5,843,228 | +15,763,172 |
| [samba](by-dataset.md#samba) | four-rank | 21,606,400 | 5,843,228 | +15,763,172 |
| [uniform](by-dataset.md#uniform) | four-direct | 25,165,824 | 25,168,140 | -2,316 |
| [uniform](by-dataset.md#uniform) | four-equivalent | 25,165,824 | 25,168,140 | -2,316 |
| [uniform](by-dataset.md#uniform) | four-joint | 25,165,824 | 25,168,140 | -2,316 |
| [uniform](by-dataset.md#uniform) | four-orbit | 25,165,824 | 25,168,140 | -2,316 |
| [uniform](by-dataset.md#uniform) | four-rank | 25,165,824 | 25,168,140 | -2,316 |

<a id="learned-cellular-rules"></a>
## Jointly learning a cellular rule and the matrix of its prediction errors

[Implementation and protocol](../../learned-cellular-rules/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| learned-field | learned-coupled | 7.9931 → 3.5692 | 7.9890 → 2.7951 | 29,389,440 → 11,276,527 |
| luma-jake | learned-coupled | 6.0905 → 1.1219 | 2.2173 → 0.4218 | 1,716,540 → 1,796,738 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [field-independent](by-dataset.md#field-independent) | learned-basis | 29,491,200 | 29,482,702 | +8,498 |
| [field-independent](by-dataset.md#field-independent) | learned-coupled | 29,491,200 | 25,262,111 | +4,229,089 |
| [field-independent](by-dataset.md#field-independent) | learned-joint | 29,491,200 | 25,262,112 | +4,229,088 |
| [field-independent](by-dataset.md#field-independent) | learned-rule | 29,491,200 | 25,262,117 | +4,229,083 |
| [field-transfer](by-dataset.md#field-transfer) | learned-coupled | 29,491,200 | 11,045,164 | +18,446,036 |
| [field-transfer](by-dataset.md#field-transfer) | learned-joint | 29,491,200 | 26,700,643 | +2,790,557 |
| [field-uniform](by-dataset.md#field-uniform) | learned-coupled | 29,491,200 | 29,491,268 | -68 |
| [field-uniform](by-dataset.md#field-uniform) | learned-direct | 29,491,200 | 29,491,268 | -68 |
| [learned-field](by-dataset.md#learned-field) | learned-basis | 29,491,200 | 29,325,778 | +165,422 |
| [learned-field](by-dataset.md#learned-field) | learned-coupled | 29,491,200 | 11,051,733 | +18,439,467 |
| [learned-field](by-dataset.md#learned-field) | learned-direct | 29,491,200 | 29,383,197 | +108,003 |
| [learned-field](by-dataset.md#learned-field) | learned-joint | 29,491,200 | 25,054,265 | +4,436,935 |
| [learned-field](by-dataset.md#learned-field) | learned-planes | 29,491,200 | 29,374,738 | +116,462 |
| [learned-field](by-dataset.md#learned-field) | learned-rule | 29,491,200 | 25,054,299 | +4,436,901 |
| [learned-field](by-dataset.md#learned-field) | learned-temporal | 29,491,200 | 29,300,409 | +190,791 |
| [luma-jake](by-dataset.md#luma-jake) | learned-basis | 29,491,200 | 1,947,559 | +27,543,641 |
| [luma-jake](by-dataset.md#luma-jake) | learned-coupled | 29,491,200 | 1,647,841 | +27,843,359 |
| [luma-jake](by-dataset.md#luma-jake) | learned-direct | 29,491,200 | 1,947,559 | +27,543,641 |
| [luma-jake](by-dataset.md#luma-jake) | learned-joint | 29,491,200 | 1,647,841 | +27,843,359 |
| [luma-jake](by-dataset.md#luma-jake) | learned-planes | 29,491,200 | 1,947,559 | +27,543,641 |
| [luma-jake](by-dataset.md#luma-jake) | learned-rule | 29,491,200 | 1,648,337 | +27,842,863 |
| [luma-jake](by-dataset.md#luma-jake) | learned-temporal | 29,491,200 | 1,648,337 | +27,842,863 |
| [luma-kath](by-dataset.md#luma-kath) | learned-basis | 29,491,200 | 1,408,574 | +28,082,626 |
| [luma-kath](by-dataset.md#luma-kath) | learned-coupled | 29,491,200 | 1,350,637 | +28,140,563 |
| [luma-kath](by-dataset.md#luma-kath) | learned-direct | 29,491,200 | 1,410,196 | +28,081,004 |
| [luma-kath](by-dataset.md#luma-kath) | learned-joint | 29,491,200 | 1,350,637 | +28,140,563 |
| [luma-kath](by-dataset.md#luma-kath) | learned-planes | 29,491,200 | 1,410,196 | +28,081,004 |
| [luma-kath](by-dataset.md#luma-kath) | learned-rule | 29,491,200 | 1,351,318 | +28,139,882 |
| [luma-kath](by-dataset.md#luma-kath) | learned-temporal | 29,491,200 | 1,351,318 | +28,139,882 |
| [luma-rei](by-dataset.md#luma-rei) | learned-basis | 29,491,200 | 5,116,313 | +24,374,887 |
| [luma-rei](by-dataset.md#luma-rei) | learned-coupled | 29,491,200 | 4,139,127 | +25,352,073 |
| [luma-rei](by-dataset.md#luma-rei) | learned-direct | 29,491,200 | 5,116,313 | +24,374,887 |
| [luma-rei](by-dataset.md#luma-rei) | learned-joint | 29,491,200 | 4,139,127 | +25,352,073 |
| [luma-rei](by-dataset.md#luma-rei) | learned-planes | 29,491,200 | 5,116,313 | +24,374,887 |
| [luma-rei](by-dataset.md#luma-rei) | learned-rule | 29,491,200 | 4,139,135 | +25,352,065 |
| [luma-rei](by-dataset.md#luma-rei) | learned-temporal | 29,491,200 | 4,139,135 | +25,352,065 |

<a id="lattice-prediction"></a>
## Local integer grids and bit-plane residuals

[Implementation and protocol](../../lattice-prediction/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| covertype-prefix | lattice-rows-field-positions | 2.2843 → 2.3029 | 1.3298 → 1.0673 | 3,997,073 → 2,493,345 |
| covertype-prefix | lattice-rows-field-prefix | 2.2843 → 2.5326 | 1.3298 → 1.2712 | 3,997,073 → 3,365,027 |
| covertype-prefix | lattice-rows-fields | 2.2843 → 2.2866 | 1.3298 → 1.3302 | 3,997,073 → 3,372,812 |
| covertype-prefix | lattice-rows-joint | 2.2843 → 1.3312 | 1.3298 → 0.9613 | 3,997,073 → 3,422,678 |
| covertype-prefix | lattice-rows-prefix | 2.2843 → 2.6163 | 1.3298 → 1.3132 | 3,997,073 → 4,185,009 |
| nci | lattice-rows-above | 2.4293 → 1.7313 | 1.9466 → 1.0145 | 2,835,396 → 3,218,569 |
| nci | lattice-rows-columns | 2.4293 → 2.4775 | 1.9466 → 0.6467 | 2,835,396 → 2,489,621 |
| nci | lattice-rows-delta | 2.4293 → 1.2887 | 1.9466 → 0.8982 | 2,835,396 → 3,259,904 |
| nci | lattice-rows-field-positions | 2.4293 → 2.4463 | 1.9466 → 1.7480 | 2,835,396 → 3,183,691 |
| nci | lattice-rows-field-prefix | 2.4293 → 2.6398 | 1.9466 → 1.9028 | 2,835,396 → 2,943,388 |
| nci | lattice-rows-fields | 2.4293 → 2.4309 | 1.9466 → 1.9466 | 2,835,396 → 2,836,967 |
| nci | lattice-rows-framed | 2.4293 → 2.4775 | 1.9466 → 1.8443 | 2,835,396 → 2,897,093 |
| nci | lattice-rows-joint | 2.4293 → 1.2887 | 1.9466 → 0.7681 | 2,835,396 → 2,761,194 |
| nci | lattice-rows-prefix | 2.4293 → 2.6393 | 1.9466 → 1.9022 | 2,835,396 → 2,942,762 |
| nci | lattice-rows-route-select | 2.4293 → 2.5964 | 1.9466 → 0.6633 | 2,835,396 → 2,483,811 |
| nci | lattice-rows-select | 2.4293 → 2.5964 | 1.9466 → 0.6633 | 2,835,396 → 2,483,811 |
| nci-row-shuffled | lattice-rows-columns | 2.4293 → 2.4775 | 2.3190 → 2.1755 | 12,578,509 → 11,833,316 |
| nci-row-shuffled | lattice-rows-delta | 2.4293 → 3.9131 | 2.3190 → 3.6970 | 12,578,509 → 18,077,269 |
| nci-row-shuffled | lattice-rows-field-positions | 2.4293 → 2.4463 | 2.3190 → 2.3469 | 12,578,509 → 12,691,175 |
| nci-row-shuffled | lattice-rows-field-prefix | 2.4293 → 2.5895 | 2.3190 → 2.3101 | 12,578,509 → 12,812,624 |
| nci-row-shuffled | lattice-rows-fields | 2.4293 → 2.4309 | 2.3190 → 2.3189 | 12,578,509 → 12,579,574 |
| nci-row-shuffled | lattice-rows-framed | 2.4293 → 2.4775 | 2.3190 → 2.1714 | 12,578,509 → 11,915,614 |
| nci-row-shuffled | lattice-rows-joint | 2.4293 → 3.9131 | 2.3190 → 2.6379 | 12,578,509 → 13,578,836 |
| nci-row-shuffled | lattice-rows-prefix | 2.4293 → 2.5891 | 2.3190 → 2.3095 | 12,578,509 → 12,811,858 |
| nci-row-shuffled | lattice-rows-route-select | 2.4293 → 2.4775 | 2.3190 → 2.1755 | 12,578,509 → 11,833,316 |
| nci-row-shuffled | lattice-rows-select | 2.4293 → 2.4775 | 2.3190 → 2.1755 | 12,578,509 → 11,833,316 |
| noaa-1990-prefix | lattice-rows-above | 3.9764 → 2.1622 | 2.6846 → 1.4320 | 3,541,939 → 3,343,075 |
| noaa-1990-prefix | lattice-rows-columns | 3.9764 → 4.0526 | 2.6846 → 1.0043 | 3,541,939 → 3,221,769 |
| noaa-1990-prefix | lattice-rows-delta | 3.9764 → 1.5805 | 2.6846 → 1.0964 | 3,541,939 → 3,835,972 |
| noaa-1990-prefix | lattice-rows-field-positions | 3.9764 → 3.9918 | 2.6846 → 0.9572 | 3,541,939 → 2,307,035 |
| noaa-1990-prefix | lattice-rows-field-prefix | 3.9764 → 3.7762 | 2.6846 → 1.9335 | 3,541,939 → 1,870,761 |
| noaa-1990-prefix | lattice-rows-fields | 3.9764 → 3.9783 | 2.6846 → 2.6957 | 3,541,939 → 2,086,007 |
| noaa-1990-prefix | lattice-rows-framed | 3.9764 → 4.0526 | 2.6846 → 2.7191 | 3,541,939 → 3,744,492 |
| noaa-1990-prefix | lattice-rows-joint | 3.9764 → 1.5805 | 2.6846 → 1.0309 | 3,541,939 → 3,402,507 |
| noaa-1990-prefix | lattice-rows-literal | 3.9764 → 3.9767 | 2.6846 → 2.6847 | 3,541,939 → 3,542,684 |
| noaa-1990-prefix | lattice-rows-positions | 3.9764 → 3.9796 | 2.6846 → 3.0985 | 3,541,939 → 3,164,406 |
| noaa-1990-prefix | lattice-rows-prefix | 3.9764 → 3.9579 | 2.6846 → 2.2792 | 3,541,939 → 3,784,147 |
| noaa-1990-prefix | lattice-rows-route-select | 3.9764 → 3.9859 | 2.6846 → 2.6750 | 3,541,939 → 2,032,120 |
| noaa-1990-prefix | lattice-rows-select | 3.9764 → 4.1541 | 2.6846 → 1.1110 | 3,541,939 → 3,216,603 |
| noaa-2020-prefix | lattice-rows-above | 3.9485 → 2.1309 | 2.8067 → 1.4288 | 3,552,108 → 3,517,969 |
| noaa-2020-prefix | lattice-rows-columns | 3.9485 → 4.0258 | 2.8067 → 1.0384 | 3,552,108 → 3,292,962 |
| noaa-2020-prefix | lattice-rows-delta | 3.9485 → 1.6280 | 2.8067 → 1.1176 | 3,552,108 → 3,888,816 |
| noaa-2020-prefix | lattice-rows-field-positions | 3.9485 → 3.9639 | 2.8067 → 0.9553 | 3,552,108 → 2,364,895 |
| noaa-2020-prefix | lattice-rows-field-prefix | 3.9485 → 3.8387 | 2.8067 → 2.0128 | 3,552,108 → 2,012,489 |
| noaa-2020-prefix | lattice-rows-fields | 3.9485 → 3.9504 | 2.8067 → 2.8159 | 3,552,108 → 2,100,930 |
| noaa-2020-prefix | lattice-rows-framed | 3.9485 → 4.0258 | 2.8067 → 2.8370 | 3,552,108 → 3,741,542 |
| noaa-2020-prefix | lattice-rows-joint | 3.9485 → 1.6280 | 2.8067 → 1.0679 | 3,552,108 → 3,474,417 |
| noaa-2020-prefix | lattice-rows-literal | 3.9485 → 3.9488 | 2.8067 → 2.8068 | 3,552,108 → 3,552,823 |
| noaa-2020-prefix | lattice-rows-positions | 3.9485 → 3.9516 | 2.8067 → 3.2197 | 3,552,108 → 3,322,140 |
| noaa-2020-prefix | lattice-rows-prefix | 3.9485 → 3.9139 | 2.8067 → 2.3761 | 3,552,108 → 3,763,027 |
| noaa-2020-prefix | lattice-rows-route-select | 3.9485 → 3.9516 | 2.8067 → 2.8413 | 3,552,108 → 2,085,342 |
| noaa-2020-prefix | lattice-rows-select | 3.9485 → 4.0258 | 2.8067 → 1.0384 | 3,552,108 → 3,292,962 |
| numerical | lattice-joint | 6.3494 → 4.9333 | 5.5271 → 3.7053 | 15,163,679 → 11,635,203 |
| uniform | lattice-rows-joint | 8.0000 → 7.9964 | 7.9981 → 7.9819 | 25,166,413 → 25,312,688 |
| uniform | lattice-rows-route-select | 8.0000 → 8.0000 | 7.9981 → 7.9981 | 25,166,413 → 25,166,905 |
| uniform | lattice-rows-select | 8.0000 → 8.0000 | 7.9981 → 7.9981 | 25,166,413 → 25,166,905 |
| webster | lattice-rows-joint | 4.9707 → 6.7647 | 3.4171 → 5.8431 | 12,107,194 → 34,326,394 |
| webster | lattice-rows-select | 4.9707 → 4.9710 | 3.4171 → 3.4171 | 12,107,194 → 12,109,357 |
| wiki-transfer | lattice-rows-field-positions | 5.0850 → 5.0990 | 3.8807 → 4.3003 | 8,968,455 → 11,111,894 |
| wiki-transfer | lattice-rows-field-prefix | 5.0850 → 5.1774 | 3.8807 → 3.8770 | 8,968,455 → 9,262,307 |
| wiki-transfer | lattice-rows-fields | 5.0850 → 5.0863 | 3.8807 → 3.8892 | 8,968,455 → 9,166,657 |
| wiki-transfer | lattice-rows-joint | 5.0850 → 6.2922 | 3.8807 → 5.3031 | 8,968,455 → 15,754,527 |
| wiki-transfer | lattice-rows-prefix | 5.0850 → 5.1749 | 3.8807 → 3.8635 | 8,968,455 → 9,089,552 |
| wiki-transfer | lattice-rows-route-select | 5.0850 → 5.0854 | 3.8807 → 3.8828 | 8,968,455 → 8,987,947 |
| wiki-transfer | lattice-rows-select | 5.0850 → 5.0852 | 3.8807 → 3.8807 | 8,968,455 → 8,968,995 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [covertype-prefix](by-dataset.md#covertype-prefix) | lattice-rows-field-positions | 25,165,824 | 2,499,177 | +22,666,647 |
| [covertype-prefix](by-dataset.md#covertype-prefix) | lattice-rows-field-prefix | 25,165,824 | 3,360,912 | +21,804,912 |
| [covertype-prefix](by-dataset.md#covertype-prefix) | lattice-rows-fields | 25,165,824 | 3,371,995 | +21,793,829 |
| [covertype-prefix](by-dataset.md#covertype-prefix) | lattice-rows-joint | 25,165,824 | 3,427,252 | +21,738,572 |
| [covertype-prefix](by-dataset.md#covertype-prefix) | lattice-rows-prefix | 25,165,824 | 4,181,076 | +20,984,748 |
| [mesa-update](by-dataset.md#mesa-update) | lattice-joint19 | 67,133,440 | 18,718,222 | +48,415,218 |
| [mozilla](by-dataset.md#mozilla) | lattice-direct | 51,220,480 | 18,547,895 | +32,672,585 |
| [mozilla](by-dataset.md#mozilla) | lattice-direct-xz | 51,220,480 | 14,330,877 | +36,889,603 |
| [mozilla](by-dataset.md#mozilla) | lattice-direct19 | 51,220,480 | 15,972,267 | +35,248,213 |
| [mozilla](by-dataset.md#mozilla) | lattice-joint | 51,220,480 | 18,528,219 | +32,692,261 |
| [mozilla](by-dataset.md#mozilla) | lattice-joint-xz | 51,220,480 | 14,328,741 | +36,891,739 |
| [mozilla](by-dataset.md#mozilla) | lattice-joint19 | 51,220,480 | 15,949,364 | +35,271,116 |
| [mozilla](by-dataset.md#mozilla) | lattice-layout | 51,220,480 | 18,528,219 | +32,692,261 |
| [mozilla](by-dataset.md#mozilla) | lattice-predict | 51,220,480 | 18,547,895 | +32,672,585 |
| [nci](by-dataset.md#nci) | lattice-direct | 33,553,445 | 2,897,140 | +30,656,305 |
| [nci](by-dataset.md#nci) | lattice-joint | 33,553,445 | 2,897,140 | +30,656,305 |
| [nci](by-dataset.md#nci) | lattice-layout | 33,553,445 | 2,897,140 | +30,656,305 |
| [nci](by-dataset.md#nci) | lattice-predict | 33,553,445 | 2,897,140 | +30,656,305 |
| [nci](by-dataset.md#nci) | lattice-rows-above | 33,553,445 | 3,210,541 | +30,342,904 |
| [nci](by-dataset.md#nci) | lattice-rows-columns | 33,553,445 | 2,499,589 | +31,053,856 |
| [nci](by-dataset.md#nci) | lattice-rows-delta | 33,553,445 | 3,252,940 | +30,300,505 |
| [nci](by-dataset.md#nci) | lattice-rows-field-positions | 33,553,445 | 3,186,434 | +30,367,011 |
| [nci](by-dataset.md#nci) | lattice-rows-field-prefix | 33,553,445 | 2,939,827 | +30,613,618 |
| [nci](by-dataset.md#nci) | lattice-rows-fields | 33,553,445 | 2,834,997 | +30,718,448 |
| [nci](by-dataset.md#nci) | lattice-rows-framed | 33,553,445 | 2,894,848 | +30,658,597 |
| [nci](by-dataset.md#nci) | lattice-rows-joint | 33,553,445 | 2,763,518 | +30,789,927 |
| [nci](by-dataset.md#nci) | lattice-rows-prefix | 33,553,445 | 2,939,148 | +30,614,297 |
| [nci](by-dataset.md#nci) | lattice-rows-route-select | 33,553,445 | 2,493,007 | +31,060,438 |
| [nci](by-dataset.md#nci) | lattice-rows-select | 33,553,445 | 2,493,007 | +31,060,438 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-columns | 33,553,445 | 11,837,029 | +21,716,416 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-delta | 33,553,445 | 18,077,240 | +15,476,205 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-field-positions | 33,553,445 | 12,695,852 | +20,857,593 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-field-prefix | 33,553,445 | 12,815,904 | +20,737,541 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-fields | 33,553,445 | 12,584,223 | +20,969,222 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-framed | 33,553,445 | 11,919,156 | +21,634,289 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-joint | 33,553,445 | 13,576,147 | +19,977,298 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-prefix | 33,553,445 | 12,813,712 | +20,739,733 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-route-select | 33,553,445 | 11,837,029 | +21,716,416 |
| [nci-row-shuffled](by-dataset.md#nci-row-shuffled) | lattice-rows-select | 33,553,445 | 11,837,029 | +21,716,416 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-above | 25,165,824 | 3,342,275 | +21,823,549 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-columns | 25,165,824 | 3,234,817 | +21,931,007 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-delta | 25,165,824 | 3,834,129 | +21,331,695 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-field-positions | 25,165,824 | 2,296,741 | +22,869,083 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-field-prefix | 25,165,824 | 1,851,287 | +23,314,537 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-fields | 25,165,824 | 2,066,584 | +23,099,240 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-framed | 25,165,824 | 3,746,780 | +21,419,044 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-joint | 25,165,824 | 3,407,235 | +21,758,589 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-literal | 25,165,824 | 3,546,099 | +21,619,725 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-positions | 25,165,824 | 3,163,742 | +22,002,082 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-prefix | 25,165,824 | 3,786,850 | +21,378,974 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-route-select | 25,165,824 | 2,014,421 | +23,151,403 |
| [noaa-1990-prefix](by-dataset.md#noaa-1990-prefix) | lattice-rows-select | 25,165,824 | 3,230,095 | +21,935,729 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-above | 25,165,824 | 3,519,194 | +21,646,630 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-columns | 25,165,824 | 3,302,573 | +21,863,251 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-delta | 25,165,824 | 3,887,200 | +21,278,624 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-field-positions | 25,165,824 | 2,354,265 | +22,811,559 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-field-prefix | 25,165,824 | 2,002,982 | +23,162,842 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-fields | 25,165,824 | 2,077,403 | +23,088,421 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-framed | 25,165,824 | 3,741,661 | +21,424,163 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-joint | 25,165,824 | 3,478,146 | +21,687,678 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-literal | 25,165,824 | 3,554,623 | +21,611,201 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-positions | 25,165,824 | 3,318,696 | +21,847,128 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-prefix | 25,165,824 | 3,767,003 | +21,398,821 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-route-select | 25,165,824 | 2,062,346 | +23,103,478 |
| [noaa-2020-prefix](by-dataset.md#noaa-2020-prefix) | lattice-rows-select | 25,165,824 | 3,302,573 | +21,863,251 |
| [numerical](by-dataset.md#numerical) | lattice-direct | 25,696,748 | 15,227,864 | +10,468,884 |
| [numerical](by-dataset.md#numerical) | lattice-direct-xz | 25,696,748 | 11,846,741 | +13,850,007 |
| [numerical](by-dataset.md#numerical) | lattice-direct19 | 25,696,748 | 13,601,994 | +12,094,754 |
| [numerical](by-dataset.md#numerical) | lattice-joint | 25,696,748 | 11,654,765 | +14,041,983 |
| [numerical](by-dataset.md#numerical) | lattice-joint-xz | 25,696,748 | 10,421,725 | +15,275,023 |
| [numerical](by-dataset.md#numerical) | lattice-joint19 | 25,696,748 | 11,006,699 | +14,690,049 |
| [numerical](by-dataset.md#numerical) | lattice-layout | 25,696,748 | 13,018,122 | +12,678,626 |
| [numerical](by-dataset.md#numerical) | lattice-predict | 25,696,748 | 13,025,639 | +12,671,109 |
| [numpy-update](by-dataset.md#numpy-update) | lattice-joint19 | 53,800,960 | 10,519,150 | +43,281,810 |
| [place-distances](by-dataset.md#place-distances) | lattice-joint19 | 21,155,400 | 13,100,968 | +8,054,432 |
| [samba](by-dataset.md#samba) | lattice-direct | 21,606,400 | 5,192,593 | +16,413,807 |
| [samba](by-dataset.md#samba) | lattice-direct-xz | 21,606,400 | 4,239,761 | +17,366,639 |
| [samba](by-dataset.md#samba) | lattice-direct19 | 21,606,400 | 4,365,638 | +17,240,762 |
| [samba](by-dataset.md#samba) | lattice-joint | 21,606,400 | 5,153,877 | +16,452,523 |
| [samba](by-dataset.md#samba) | lattice-joint-xz | 21,606,400 | 4,239,761 | +17,366,639 |
| [samba](by-dataset.md#samba) | lattice-joint19 | 21,606,400 | 4,365,148 | +17,241,252 |
| [samba](by-dataset.md#samba) | lattice-layout | 21,606,400 | 5,153,877 | +16,452,523 |
| [samba](by-dataset.md#samba) | lattice-predict | 21,606,400 | 5,192,593 | +16,413,807 |
| [uniform](by-dataset.md#uniform) | lattice-direct | 25,165,824 | 25,166,052 | -228 |
| [uniform](by-dataset.md#uniform) | lattice-direct-xz | 25,165,824 | 25,166,052 | -228 |
| [uniform](by-dataset.md#uniform) | lattice-direct19 | 25,165,824 | 25,166,052 | -228 |
| [uniform](by-dataset.md#uniform) | lattice-joint | 25,165,824 | 25,166,052 | -228 |
| [uniform](by-dataset.md#uniform) | lattice-joint-xz | 25,165,824 | 25,166,052 | -228 |
| [uniform](by-dataset.md#uniform) | lattice-joint19 | 25,165,824 | 25,166,052 | -228 |
| [uniform](by-dataset.md#uniform) | lattice-layout | 25,165,824 | 25,166,052 | -228 |
| [uniform](by-dataset.md#uniform) | lattice-predict | 25,165,824 | 25,166,052 | -228 |
| [uniform](by-dataset.md#uniform) | lattice-rows-joint | 25,165,824 | 25,312,692 | -146,868 |
| [uniform](by-dataset.md#uniform) | lattice-rows-route-select | 25,165,824 | 25,166,909 | -1,085 |
| [uniform](by-dataset.md#uniform) | lattice-rows-select | 25,165,824 | 25,166,909 | -1,085 |
| [walk-distances](by-dataset.md#walk-distances) | lattice-joint19 | 21,155,400 | 8,773,798 | +12,381,602 |
| [webster](by-dataset.md#webster) | lattice-rows-joint | 41,458,703 | 34,320,561 | +7,138,142 |
| [webster](by-dataset.md#webster) | lattice-rows-select | 41,458,703 | 12,097,762 | +29,360,941 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-direct | 25,165,824 | 9,108,718 | +16,057,106 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-direct-xz | 25,165,824 | 7,602,472 | +17,563,352 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-direct19 | 25,165,824 | 7,824,376 | +17,341,448 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-joint | 25,165,824 | 9,108,718 | +16,057,106 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-joint-xz | 25,165,824 | 7,602,472 | +17,563,352 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-joint19 | 25,165,824 | 7,824,376 | +17,341,448 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-layout | 25,165,824 | 9,108,718 | +16,057,106 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-predict | 25,165,824 | 9,108,718 | +16,057,106 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-rows-field-positions | 25,165,824 | 11,108,131 | +14,057,693 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-rows-field-prefix | 25,165,824 | 9,257,618 | +15,908,206 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-rows-fields | 25,165,824 | 9,169,822 | +15,996,002 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-rows-joint | 25,165,824 | 15,741,722 | +9,424,102 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-rows-prefix | 25,165,824 | 9,083,523 | +16,082,301 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-rows-route-select | 25,165,824 | 8,983,638 | +16,182,186 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | lattice-rows-select | 25,165,824 | 8,962,957 | +16,202,867 |

<a id="distance-geometry"></a>
## Distance matrices reconstructed from landmarks

[Implementation and protocol](../../distance-geometry/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [arc-distances](by-dataset.md#arc-distances) | distance-all | 21,155,400 | 4,242,861 | +16,912,539 |
| [arc-distances](by-dataset.md#arc-distances) | distance-direct | 21,155,400 | 19,891,770 | +1,263,630 |
| [arc-distances](by-dataset.md#arc-distances) | distance-rows | 21,155,400 | 13,383,793 | +7,771,607 |
| [arc-distances](by-dataset.md#arc-distances) | distance-sphere | 21,155,400 | 4,242,861 | +16,912,539 |
| [arc-distances](by-dataset.md#arc-distances) | distance-three | 21,155,400 | 14,975,990 | +6,179,410 |
| [place-distances](by-dataset.md#place-distances) | distance-direct | 21,155,400 | 20,027,877 | +1,127,523 |
| [place-distances](by-dataset.md#place-distances) | distance-joint | 21,155,400 | 3,850,014 | +17,305,386 |
| [place-distances](by-dataset.md#place-distances) | distance-rows | 21,155,400 | 14,052,449 | +7,102,951 |
| [place-distances](by-dataset.md#place-distances) | distance-three | 21,155,400 | 3,850,014 | +17,305,386 |
| [place-distances](by-dataset.md#place-distances) | distance-two | 21,155,400 | 14,554,691 | +6,600,709 |
| [random-triangle](by-dataset.md#random-triangle) | distance-all | 21,155,400 | 21,155,413 | -13 |
| [random-triangle](by-dataset.md#random-triangle) | distance-direct | 21,155,400 | 21,155,413 | -13 |
| [random-triangle](by-dataset.md#random-triangle) | distance-rows | 21,155,400 | 21,155,413 | -13 |
| [random-triangle](by-dataset.md#random-triangle) | distance-sphere | 21,155,400 | 21,155,413 | -13 |
| [random-triangle](by-dataset.md#random-triangle) | distance-three | 21,155,400 | 21,155,413 | -13 |
| [walk-distances](by-dataset.md#walk-distances) | distance-direct | 21,155,400 | 20,725,737 | +429,663 |
| [walk-distances](by-dataset.md#walk-distances) | distance-joint | 21,155,400 | 2,860,313 | +18,295,087 |
| [walk-distances](by-dataset.md#walk-distances) | distance-rows | 21,155,400 | 10,164,974 | +10,990,426 |
| [walk-distances](by-dataset.md#walk-distances) | distance-three | 21,155,400 | 2,860,313 | +18,295,087 |
| [walk-distances](by-dataset.md#walk-distances) | distance-two | 21,155,400 | 2,925,332 | +18,230,068 |

<a id="shape-context"></a>
## Raster shape search with an actual range-coded archive

[Implementation and protocol](../../shape-context/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [manual-graphs](by-dataset.md#manual-graphs) | shape | 24,642,792 | 901,604 | +23,741,188 |
| [manual-library](by-dataset.md#manual-library) | shape | 24,283,584 | 1,283,911 | +22,999,673 |
| [manual-transfer](by-dataset.md#manual-transfer) | shape | 31,809,024 | 1,331,683 | +30,477,341 |
| [nci](by-dataset.md#nci) | shape | 33,553,445 | 8,743,426 | +24,810,019 |
| [numerical](by-dataset.md#numerical) | shape | 25,696,748 | 16,165,523 | +9,531,225 |
| [samba](by-dataset.md#samba) | shape | 21,606,400 | 15,955,462 | +5,650,938 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | shape | 25,165,824 | 20,974,546 | +4,191,278 |

<a id="glyph-residuals"></a>
## Repeated glyphs and an exact bitmap residual

[Implementation and protocol](../../glyph-residuals/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [manual-graphs](by-dataset.md#manual-graphs) | glyph-direct | 24,642,792 | 1,206,504 | +23,436,288 |
| [manual-graphs](by-dataset.md#manual-graphs) | glyph-fuzzy | 24,642,792 | 337,192 | +24,305,600 |
| [manual-graphs](by-dataset.md#manual-graphs) | glyph-glyphs | 24,642,792 | 338,447 | +24,304,345 |
| [manual-graphs](by-dataset.md#manual-graphs) | glyph-jbig | 24,642,792 | 707,818 | +23,934,974 |
| [manual-graphs](by-dataset.md#manual-graphs) | glyph-joint | 24,642,792 | 211,517 | +24,431,275 |
| [manual-graphs](by-dataset.md#manual-graphs) | glyph-position | 24,642,792 | 189,603 | +24,453,189 |
| [manual-library](by-dataset.md#manual-library) | glyph-direct | 24,283,584 | 1,705,163 | +22,578,421 |
| [manual-library](by-dataset.md#manual-library) | glyph-fuzzy | 24,283,584 | 277,021 | +24,006,563 |
| [manual-library](by-dataset.md#manual-library) | glyph-glyphs | 24,283,584 | 277,021 | +24,006,563 |
| [manual-library](by-dataset.md#manual-library) | glyph-jbig | 24,283,584 | 1,049,885 | +23,233,699 |
| [manual-library](by-dataset.md#manual-library) | glyph-joint | 24,283,584 | 196,530 | +24,087,054 |
| [manual-library](by-dataset.md#manual-library) | glyph-position | 24,283,584 | 160,297 | +24,123,287 |
| [manual-transfer](by-dataset.md#manual-transfer) | glyph-direct | 31,809,024 | 1,796,363 | +30,012,661 |
| [manual-transfer](by-dataset.md#manual-transfer) | glyph-fuzzy | 31,809,024 | 257,250 | +31,551,774 |
| [manual-transfer](by-dataset.md#manual-transfer) | glyph-glyphs | 31,809,024 | 257,250 | +31,551,774 |
| [manual-transfer](by-dataset.md#manual-transfer) | glyph-joint | 31,809,024 | 225,552 | +31,583,472 |
| [manual-transfer](by-dataset.md#manual-transfer) | glyph-position | 31,809,024 | 195,223 | +31,613,801 |
| [manual-valgrind](by-dataset.md#manual-valgrind) | glyph-joint | 30,924,288 | 435,746 | +30,488,542 |
| [manual-valgrind](by-dataset.md#manual-valgrind) | glyph-position | 30,924,288 | 394,104 | +30,530,184 |

<a id="text-views"></a>
## Text fields, BWT and move-to-front

[Implementation and protocol](../../text-views/README.md)

**Preprocessing before Zstandard 3**

| Input | Profile | Byte entropy H0 before → after | Conditional entropy H1 before → after | Zstd bytes before → after |
|---|---|---:|---:|---:|
| wiki-transfer | views-bwt | 5.0850 → 5.0851 | 3.8807 → 2.8011 | 8,968,455 → 8,800,771 |
| wiki-transfer | views-mtf | 5.0850 → 2.6119 | 3.8807 → 2.3702 | 8,968,455 → 8,662,902 |

**Standalone archive sizes**

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [enwik8](by-dataset.md#enwik8) | views-bwt | 100,000,000 | 34,640,737 | +65,359,263 |
| [enwik8](by-dataset.md#enwik8) | views-joint | 100,000,000 | 32,539,733 | +67,460,267 |
| [enwik8](by-dataset.md#enwik8) | views-mtf | 100,000,000 | 34,159,835 | +65,840,165 |
| [enwik9](by-dataset.md#enwik9) | views-bwt | 1,000,000,000 | 303,703,378 | +696,296,622 |
| [enwik9](by-dataset.md#enwik9) | views-direct | 1,000,000,000 | 314,928,681 | +685,071,319 |
| [enwik9](by-dataset.md#enwik9) | views-mtf | 1,000,000,000 | 299,270,871 | +700,729,129 |
| [nci](by-dataset.md#nci) | views-bwt | 33,553,445 | 2,280,687 | +31,272,758 |
| [nci](by-dataset.md#nci) | views-direct | 33,553,445 | 2,864,760 | +30,688,685 |
| [nci](by-dataset.md#nci) | views-joint | 33,553,445 | 2,280,295 | +31,273,150 |
| [nci](by-dataset.md#nci) | views-mtf | 33,553,445 | 2,280,687 | +31,272,758 |
| [nci](by-dataset.md#nci) | views-text | 33,553,445 | 2,855,044 | +30,698,401 |
| [wiki-dev](by-dataset.md#wiki-dev) | views-bwt | 25,165,824 | 8,728,653 | +16,437,171 |
| [wiki-dev](by-dataset.md#wiki-dev) | views-direct | 25,165,824 | 9,022,572 | +16,143,252 |
| [wiki-dev](by-dataset.md#wiki-dev) | views-joint | 25,165,824 | 8,214,112 | +16,951,712 |
| [wiki-dev](by-dataset.md#wiki-dev) | views-mtf | 25,165,824 | 8,613,021 | +16,552,803 |
| [wiki-dev](by-dataset.md#wiki-dev) | views-text | 25,165,824 | 8,795,530 | +16,370,294 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | views-bwt | 25,165,824 | 8,759,477 | +16,406,347 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | views-direct | 25,165,824 | 9,032,653 | +16,133,171 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | views-joint | 25,165,824 | 8,231,816 | +16,934,008 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | views-mtf | 25,165,824 | 8,637,232 | +16,528,592 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | views-text | 25,165,824 | 8,804,216 | +16,361,608 |

<a id="wiki-structures"></a>
## Wikipedia page order, algebraic templates and primed context mixing

[Implementation and protocol](../../wiki-structures/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [wiki-dev](by-dataset.md#wiki-dev) | wiki-direct | 25,165,824 | 8,267,789 | +16,898,035 |
| [wiki-dev](by-dataset.md#wiki-dev) | wiki-direct-xz | 25,165,824 | 6,914,621 | +18,251,203 |
| [wiki-dev](by-dataset.md#wiki-dev) | wiki-joint | 25,165,824 | 8,223,663 | +16,942,161 |
| [wiki-dev](by-dataset.md#wiki-dev) | wiki-joint-xz | 25,165,824 | 6,894,633 | +18,271,191 |
| [wiki-dev](by-dataset.md#wiki-dev) | wiki-links | 25,165,824 | 8,267,789 | +16,898,035 |
| [wiki-dev](by-dataset.md#wiki-dev) | wiki-ordering | 25,165,824 | 8,233,638 | +16,932,186 |
| [wiki-dev](by-dataset.md#wiki-dev) | wiki-templates | 25,165,824 | 8,255,626 | +16,910,198 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wcm-literal | 25,165,824 | 5,345,330 | +19,820,494 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wcm-literal-primed | 25,165,824 | 5,331,459 | +19,834,365 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wcm-similar-template-primed | 25,165,824 | 5,312,277 | +19,853,547 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wiki-direct | 25,165,824 | 8,283,833 | +16,881,991 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wiki-direct-xz | 25,165,824 | 6,939,917 | +18,225,907 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wiki-joint | 25,165,824 | 8,223,878 | +16,941,946 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wiki-joint-xz | 25,165,824 | 6,915,857 | +18,249,967 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wiki-links | 25,165,824 | 8,283,833 | +16,881,991 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wiki-ordering | 25,165,824 | 8,229,885 | +16,935,939 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | wiki-templates | 25,165,824 | 8,275,996 | +16,889,828 |

<a id="arithmetic-references"></a>
## Conditional patches after arithmetic alignment

[Implementation and protocol](../../arithmetic-references/README.md)

| Input | Profile | Raw bytes | Archive bytes | Archive + required reference (bytes) | Bytes saved |
|---|---|---:|---:|---:|---:|
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | relative-direct (fx2-cmix-t-awarded.archive9) | 96,994,187 | 96,996,466 | 96,996,466 | -2,279 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | relative-exact (fx2-cmix-t-awarded.archive9) | 96,994,187 | 96,996,466 | 96,996,466 | -2,279 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | relative-exact (fx2-cmix-transformer-archive9.bin) | 96,994,187 | 46 | 96,994,234 | -47 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | relative-joint (fx2-cmix-t-awarded.archive9) | 96,994,187 | 96,996,466 | 96,996,466 | -2,279 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | relative-joint (fx2-cmix-transformer-archive9.bin) | 96,994,187 | 3,028 | 96,997,216 | -3,029 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | relative-numeric (fx2-cmix-t-awarded.archive9) | 96,994,187 | 96,996,466 | 96,996,466 | -2,279 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | relative-numeric (fx2-cmix-transformer-archive9.bin) | 96,994,187 | 3,028 | 96,997,216 | -3,029 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | relative-patch (fx2-cmix-t-awarded.archive9) | 96,994,187 | 96,996,466 | 96,996,466 | -2,279 |
| [cofattore-Q.base256](by-dataset.md#cofattore-qbase256) | relative-patch (fx2-cmix-transformer-archive9.bin) | 96,994,187 | 96,996,466 | 96,996,466 | -2,279 |
| [mesa-update](by-dataset.md#mesa-update) | relative-direct (mesa-base) | 67,133,440 | 19,832,536 | 19,832,536 | +47,300,904 |
| [mesa-update](by-dataset.md#mesa-update) | relative-joint (mesa-base) | 67,133,440 | 13,146,431 | 79,307,071 | -12,173,631 |
| [mesa-update](by-dataset.md#mesa-update) | relative-numeric (mesa-base) | 67,133,440 | 19,832,536 | 19,832,536 | +47,300,904 |
| [mesa-update](by-dataset.md#mesa-update) | relative-patch (mesa-base) | 67,133,440 | 13,146,431 | 79,307,071 | -12,173,631 |
| [numpy-update](by-dataset.md#numpy-update) | relative-direct (numpy-base) | 53,800,960 | 10,201,056 | 10,201,056 | +43,599,904 |
| [numpy-update](by-dataset.md#numpy-update) | relative-joint (numpy-base) | 53,800,960 | 1,347,467 | 55,066,507 | -1,265,547 |
| [numpy-update](by-dataset.md#numpy-update) | relative-numeric (numpy-base) | 53,800,960 | 10,201,056 | 10,201,056 | +43,599,904 |
| [numpy-update](by-dataset.md#numpy-update) | relative-patch (numpy-base) | 53,800,960 | 1,347,467 | 55,066,507 | -1,265,547 |

<a id="reversible-wavelets"></a>
## Integer lifting and color differences

[Implementation and protocol](../../reversible-wavelets/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [wall0.ppm](by-dataset.md#wall0ppm) | wavelet-color | 99,532,817 | 19,619,307 | +79,913,510 |
| [wall0.ppm](by-dataset.md#wall0ppm) | wavelet-direct | 99,532,817 | 19,630,612 | +79,902,205 |
| [wall0.ppm](by-dataset.md#wall0ppm) | wavelet-joint | 99,532,817 | 19,619,307 | +79,913,510 |
| [wall0.ppm](by-dataset.md#wall0ppm) | wavelet-lifting | 99,532,817 | 19,630,612 | +79,902,205 |
| [wall1.ppm](by-dataset.md#wall1ppm) | wavelet-color | 99,532,817 | 644,213 | +98,888,604 |
| [wall1.ppm](by-dataset.md#wall1ppm) | wavelet-direct | 99,532,817 | 644,213 | +98,888,604 |
| [wall1.ppm](by-dataset.md#wall1ppm) | wavelet-joint | 99,532,817 | 644,213 | +98,888,604 |
| [wall1.ppm](by-dataset.md#wall1ppm) | wavelet-lifting | 99,532,817 | 644,213 | +98,888,604 |
| [wall2.ppm](by-dataset.md#wall2ppm) | wavelet-color | 96,560,657 | 37,365,473 | +59,195,184 |
| [wall2.ppm](by-dataset.md#wall2ppm) | wavelet-direct | 96,560,657 | 37,922,336 | +58,638,321 |
| [wall2.ppm](by-dataset.md#wall2ppm) | wavelet-joint | 96,560,657 | 32,392,630 | +64,168,027 |
| [wall2.ppm](by-dataset.md#wall2ppm) | wavelet-lifting | 96,560,657 | 32,521,660 | +64,038,997 |

<a id="motion-residuals"></a>
## Motion and spatial residuals on grayscale frame sequences

[Implementation and protocol](../../motion-residuals/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [luma-jake](by-dataset.md#luma-jake) | motion-direct | 29,491,200 | 9,488,913 | +20,002,287 |
| [luma-jake](by-dataset.md#luma-jake) | motion-joint | 29,491,200 | 1,188,089 | +28,303,111 |
| [luma-jake](by-dataset.md#luma-jake) | motion-motion | 29,491,200 | 1,201,281 | +28,289,919 |
| [luma-jake](by-dataset.md#luma-jake) | motion-spatial | 29,491,200 | 7,865,422 | +21,625,778 |
| [luma-jake](by-dataset.md#luma-jake) | motion-time | 29,491,200 | 1,201,348 | +28,289,852 |
| [luma-kath](by-dataset.md#luma-kath) | motion-direct | 29,491,200 | 9,451,851 | +20,039,349 |
| [luma-kath](by-dataset.md#luma-kath) | motion-joint | 29,491,200 | 1,102,656 | +28,388,544 |
| [luma-kath](by-dataset.md#luma-kath) | motion-motion | 29,491,200 | 1,168,013 | +28,323,187 |
| [luma-kath](by-dataset.md#luma-kath) | motion-spatial | 29,491,200 | 6,898,428 | +22,592,772 |
| [luma-kath](by-dataset.md#luma-kath) | motion-time | 29,491,200 | 1,170,541 | +28,320,659 |
| [luma-rei](by-dataset.md#luma-rei) | motion-direct | 29,491,200 | 7,416,559 | +22,074,641 |
| [luma-rei](by-dataset.md#luma-rei) | motion-joint | 29,491,200 | 3,882,245 | +25,608,955 |
| [luma-rei](by-dataset.md#luma-rei) | motion-motion | 29,491,200 | 3,889,130 | +25,602,070 |
| [luma-rei](by-dataset.md#luma-rei) | motion-spatial | 29,491,200 | 6,297,844 | +23,193,356 |
| [luma-rei](by-dataset.md#luma-rei) | motion-time | 29,491,200 | 3,890,440 | +25,600,760 |

<a id="context-mixer"></a>
## CM3 context mixing

[Implementation and protocol](../../context-mixer/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [wiki-dev](by-dataset.md#wiki-dev) | cm3-context | 25,165,824 | 5,128,905 | +20,036,919 |
| [wiki-dev](by-dataset.md#wiki-dev) | cm3-lstm32 | 25,165,824 | 4,997,716 | +20,168,108 |
| [wiki-dev](by-dataset.md#wiki-dev) | cm3-mix | 25,165,824 | 5,017,931 | +20,147,893 |

<a id="statico"></a>
## Statico M1 grammar compressor

[Implementation and protocol](../../statico/README.md)

| Input | Profile | Raw bytes | Archive bytes | Bytes saved |
|---|---|---:|---:|---:|
| [enwik8](by-dataset.md#enwik8) | statico | 100,000,000 | 26,346,968 | +73,653,032 |
| [nci](by-dataset.md#nci) | statico | 33,553,445 | 1,686,759 | +31,866,686 |
| [numerical](by-dataset.md#numerical) | statico | 25,696,748 | 14,428,360 | +11,268,388 |
| [samba](by-dataset.md#samba) | statico | 21,606,400 | 4,760,025 | +16,846,375 |
| [wiki-transfer](by-dataset.md#wiki-transfer) | statico | 25,165,824 | 7,063,035 | +18,102,789 |
