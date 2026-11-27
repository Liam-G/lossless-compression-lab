# Preprocessing before standard compression

159 measured input/profile pairs on 26 distinct inputs. Each raw input is at least 20 MiB. Each pair uses exactly the same source bytes on both paths.

1. Compress the original input directly with gzip, Zstandard or XZ.
2. Serialize the reversible preprocessing output, including headers, choices, lengths, dictionaries, model parameters, literal fallbacks and residuals. Measure this stream before backend compression, then compress it with the same executable and settings as the original.
3. Decompress both paths and compare every byte. An independent invocation of the inverse preprocessor must also recover the original input exactly.

## Empirical entropy before and after preprocessing

**H0** is the entropy of the observed byte histogram. **H1** is the entropy of the next byte given the immediately preceding byte, weighted by observed adjacent pairs. Both are in bits per byte of their own stream. The first byte has no predecessor. **Post H0 per input byte** multiplies post H0 by prepared length / original length, so a shorter representation with higher byte entropy can still score well. These are empirical coding estimates for two simple models.

| Input | Preprocessor | Original bytes | Prepared bytes | H0 before → after | H1 before → after | Post H0 per input byte |
|---|---|---:|---:|---:|---:|---:|
| affine-pairs | pilot10-conditional | 25,165,824 | 15,979,518 | 3.7941 → 4.8886 | 2.3861 → 3.4200 | 3.1041 |
| affine-pairs | pilot10-fixed | 25,165,824 | 6,304,526 | 3.7941 → 7.9116 | 2.3861 → 7.8929 | 1.9820 |
| covertype-prefix | lattice-rows-field-positions | 25,165,824 | 25,215,468 | 2.2843 → 2.3029 | 1.3298 → 1.0673 | 2.3075 |
| covertype-prefix | lattice-rows-field-prefix | 25,165,824 | 26,256,422 | 2.2843 → 2.5326 | 1.3298 → 1.2712 | 2.6424 |
| covertype-prefix | lattice-rows-fields | 25,165,824 | 25,169,388 | 2.2843 → 2.2866 | 1.3298 → 1.3302 | 2.2869 |
| covertype-prefix | lattice-rows-joint | 25,165,824 | 25,166,796 | 2.2843 → 1.3312 | 1.3298 → 0.9613 | 1.3312 |
| covertype-prefix | lattice-rows-prefix | 25,165,824 | 27,491,616 | 2.2843 → 2.6163 | 1.3298 → 1.3132 | 2.8581 |
| evolved-stamps | checker-bitmap-direct-book | 28,311,552 | 4,829,851 | 1.9696 → 6.4078 | 1.9232 → 4.6752 | 1.0931 |
| evolved-stamps | checker-bitmap-direct-flat | 28,311,552 | 28,314,124 | 1.9696 → 1.9696 | 1.9232 → 1.9232 | 1.9698 |
| evolved-stamps | checker-bitmap-direct-tree | 28,311,552 | 9,593,235 | 1.9696 → 5.2001 | 1.9232 → 2.3533 | 1.7620 |
| evolved-stamps | checker-bitmap-orbit-book | 28,311,552 | 885,494 | 1.9696 → 6.9038 | 1.9232 → 5.3183 | 0.2159 |
| evolved-stamps | checker-bitmap-orbit-flat | 28,311,552 | 28,314,124 | 1.9696 → 1.4372 | 1.9232 → 1.4113 | 1.4373 |
| evolved-stamps | checker-bitmap-orbit-hot | 28,311,552 | 884,982 | 1.9696 → 6.8986 | 1.9232 → 5.3806 | 0.2156 |
| evolved-stamps | checker-bitmap-orbit-hotplanes | 28,311,552 | 884,982 | 1.9696 → 6.8982 | 1.9232 → 5.9038 | 0.2156 |
| evolved-stamps | checker-bitmap-orbit-planes | 28,311,552 | 3,849,414 | 1.9696 → 7.3016 | 1.9232 → 5.7304 | 0.9928 |
| evolved-stamps | checker-bitmap-orbit-tree | 28,311,552 | 3,849,414 | 1.9696 → 7.3024 | 1.9232 → 2.0626 | 0.9929 |
| evolved-stamps | checker-bitmap-rotated-book | 28,311,552 | 10,114,461 | 1.9696 → 6.0024 | 1.9232 → 4.8330 | 2.1444 |
| evolved-stamps | checker-bitmap-select | 28,311,552 | 885,494 | 1.9696 → 6.9038 | 1.9232 → 5.3183 | 0.2159 |
| evolved-stamps | checker-bitmap-xor-book | 28,311,552 | 5,092,083 | 1.9696 → 6.4980 | 1.9232 → 4.8623 | 1.1687 |
| evolved-stamps | checker-bitmap-xor-flat | 28,311,552 | 28,314,124 | 1.9696 → 2.0309 | 1.9232 → 1.9871 | 2.0311 |
| evolved-stamps | checker-bitmap-xor-tree | 28,311,552 | 9,593,235 | 1.9696 → 5.2846 | 1.9232 → 2.6072 | 1.7906 |
| formula-text | pilot11-dag | 25,165,824 | 9,357,678 | 3.6110 → 4.7847 | 1.1528 → 1.7253 | 1.7791 |
| graphs-shuffled-lines | checker-bitmap-direct-book | 24,642,792 | 7,403,073 | 0.7646 → 4.1137 | 0.5291 → 3.6116 | 1.2358 |
| graphs-shuffled-lines | checker-bitmap-direct-flat | 24,642,792 | 24,650,434 | 0.7646 → 0.7646 | 0.5291 → 0.5292 | 0.7649 |
| graphs-shuffled-lines | checker-bitmap-direct-tree | 24,642,792 | 9,598,949 | 0.7646 → 2.0176 | 0.5291 → 1.8635 | 0.7859 |
| graphs-shuffled-lines | checker-bitmap-orbit-book | 24,642,792 | 10,298,117 | 0.7646 → 5.7467 | 0.5291 → 4.8523 | 2.4015 |
| graphs-shuffled-lines | checker-bitmap-select | 24,642,792 | 24,650,434 | 0.7646 → 0.7646 | 0.5291 → 0.5292 | 0.7649 |
| graphs-shuffled-lines | checker-bitmap-xor-flat | 24,642,792 | 24,650,434 | 0.7646 → 1.3353 | 0.5291 → 0.9789 | 1.3358 |
| graphs-shuffled-lines | checker-bitmap-xor-hotplanes | 24,642,792 | 7,200,199 | 0.7646 → 4.0479 | 0.5291 → 3.3618 | 1.1827 |
| graphs-shuffled-lines | checker-bitmap-xor-tree | 24,642,792 | 10,244,921 | 0.7646 → 3.0310 | 0.5291 → 2.2780 | 1.2601 |
| hidden-products | shared-shared | 25,165,824 | 13,379,724 | 6.3745 → 7.9279 | 4.3616 → 7.7994 | 4.2150 |
| learned-field | learned-coupled | 29,491,200 | 29,491,588 | 7.9931 → 3.5692 | 7.9890 → 2.7951 | 3.5693 |
| luma-jake | learned-coupled | 29,491,200 | 29,491,324 | 6.0905 → 1.1219 | 2.2173 → 0.4218 | 1.1219 |
| manual-graphs | checker-bitmap-direct-book | 24,642,792 | 2,850,113 | 0.7646 → 5.4081 | 0.5291 → 4.0221 | 0.6255 |
| manual-graphs | checker-bitmap-direct-flat | 24,642,792 | 24,650,434 | 0.7646 → 0.7646 | 0.5291 → 0.5292 | 0.7649 |
| manual-graphs | checker-bitmap-direct-hot | 24,642,792 | 2,531,379 | 0.7646 → 4.7870 | 0.5291 → 3.2825 | 0.4917 |
| manual-graphs | checker-bitmap-direct-hotplanes | 24,642,792 | 2,531,379 | 0.7646 → 4.7870 | 0.5291 → 4.1411 | 0.4917 |
| manual-graphs | checker-bitmap-direct-planes | 24,642,792 | 2,926,539 | 0.7646 → 4.6161 | 0.5291 → 3.6930 | 0.5482 |
| manual-graphs | checker-bitmap-direct-tree | 24,642,792 | 2,926,539 | 0.7646 → 4.6152 | 0.5291 → 2.9137 | 0.5481 |
| manual-graphs | checker-bitmap-orbit-book | 24,642,792 | 3,323,668 | 0.7646 → 5.8915 | 0.5291 → 5.1405 | 0.7946 |
| manual-graphs | checker-bitmap-orbit-flat | 24,642,792 | 24,650,434 | 0.7646 → 0.9611 | 0.5291 → 0.6964 | 0.9614 |
| manual-graphs | checker-bitmap-orbit-tree | 24,642,792 | 3,393,558 | 0.7646 → 5.1915 | 0.5291 → 4.1933 | 0.7149 |
| manual-graphs | checker-bitmap-select | 24,642,792 | 6,123,631 | 0.7646 → 2.0863 | 0.5291 → 1.6433 | 0.5184 |
| manual-graphs | checker-bitmap-xor-book | 24,642,792 | 2,920,517 | 0.7646 → 4.6615 | 0.5291 → 4.0528 | 0.5524 |
| manual-graphs | checker-bitmap-xor-flat | 24,642,792 | 24,650,434 | 0.7646 → 0.5581 | 0.5291 → 0.4053 | 0.5583 |
| manual-graphs | checker-bitmap-xor-hot | 24,642,792 | 2,608,143 | 0.7646 → 3.8982 | 0.5291 → 3.3043 | 0.4126 |
| manual-graphs | checker-bitmap-xor-hotplanes | 24,642,792 | 2,608,143 | 0.7646 → 3.8980 | 0.5291 → 3.4410 | 0.4126 |
| manual-graphs | checker-bitmap-xor-planes | 24,642,792 | 2,904,414 | 0.7646 → 3.7019 | 0.5291 → 2.9840 | 0.4363 |
| manual-graphs | checker-bitmap-xor-tree | 24,642,792 | 2,904,414 | 0.7646 → 3.7017 | 0.5291 → 2.9808 | 0.4363 |
| manual-graphs | pilot07-pre-1 | 24,642,792 | 3,112,119 | 0.7646 → 6.8702 | 0.5291 → 5.9196 | 0.8676 |
| manual-library | checker-bitmap-direct-book | 24,283,584 | 3,978,731 | 1.0898 → 5.5074 | 0.7688 → 4.0516 | 0.9024 |
| manual-library | checker-bitmap-direct-tree | 24,283,584 | 4,329,338 | 1.0898 → 4.5936 | 0.7688 → 2.8490 | 0.8190 |
| manual-library | checker-bitmap-orbit-book | 24,283,584 | 4,623,892 | 1.0898 → 5.9495 | 0.7688 → 5.1475 | 1.1329 |
| manual-library | checker-bitmap-select | 24,283,584 | 5,661,943 | 1.0898 → 3.0788 | 0.7688 → 2.4187 | 0.7179 |
| manual-library | checker-bitmap-xor-book | 24,283,584 | 4,064,989 | 1.0898 → 4.7625 | 0.7688 → 4.0913 | 0.7972 |
| manual-library | checker-bitmap-xor-flat | 24,283,584 | 24,290,980 | 1.0898 → 0.7858 | 0.7688 → 0.5951 | 0.7861 |
| manual-library | checker-bitmap-xor-hot | 24,283,584 | 3,703,395 | 1.0898 → 4.0059 | 0.7688 → 3.3646 | 0.6109 |
| manual-library | checker-bitmap-xor-hotplanes | 24,283,584 | 3,703,395 | 1.0898 → 4.0058 | 0.7688 → 3.5299 | 0.6109 |
| manual-library | checker-bitmap-xor-planes | 24,283,584 | 4,312,007 | 1.0898 → 3.6490 | 0.7688 → 2.9694 | 0.6479 |
| manual-library | checker-bitmap-xor-tree | 24,283,584 | 4,312,007 | 1.0898 → 3.6489 | 0.7688 → 2.9336 | 0.6479 |
| manual-transfer | checker-bitmap-direct-book | 31,809,024 | 4,542,839 | 0.9931 → 5.4695 | 0.6449 → 3.8703 | 0.7811 |
| manual-transfer | checker-bitmap-direct-tree | 31,809,024 | 5,197,543 | 0.9931 → 4.4275 | 0.6449 → 2.6278 | 0.7235 |
| manual-transfer | checker-bitmap-orbit-book | 31,809,024 | 5,251,862 | 0.9931 → 5.9091 | 0.6449 → 4.9348 | 0.9756 |
| manual-transfer | checker-bitmap-select | 31,809,024 | 13,353,597 | 0.9931 → 1.6982 | 0.6449 → 1.3089 | 0.7129 |
| manual-transfer | checker-bitmap-xor-book | 31,809,024 | 4,537,674 | 0.9931 → 4.6357 | 0.6449 → 3.9871 | 0.6613 |
| manual-transfer | checker-bitmap-xor-flat | 31,809,024 | 31,811,916 | 0.9931 → 0.6563 | 0.6449 → 0.5019 | 0.6563 |
| manual-transfer | checker-bitmap-xor-hot | 31,809,024 | 4,023,794 | 0.9931 → 4.0289 | 0.6449 → 3.4131 | 0.5097 |
| manual-transfer | checker-bitmap-xor-hotplanes | 31,809,024 | 4,023,794 | 0.9931 → 4.0286 | 0.6449 → 3.5358 | 0.5096 |
| manual-transfer | checker-bitmap-xor-planes | 31,809,024 | 5,128,749 | 0.9931 → 3.3440 | 0.6449 → 2.6874 | 0.5392 |
| manual-transfer | checker-bitmap-xor-tree | 31,809,024 | 5,128,749 | 0.9931 → 3.3438 | 0.6449 → 2.7025 | 0.5391 |
| manual-valgrind | checker-bitmap-direct-book | 30,924,288 | 6,350,615 | 1.3043 → 5.5204 | 0.8091 → 4.0915 | 1.1337 |
| manual-valgrind | checker-bitmap-direct-tree | 30,924,288 | 8,011,199 | 1.3043 → 4.0819 | 0.8091 → 2.5323 | 1.0575 |
| manual-valgrind | checker-bitmap-orbit-book | 30,924,288 | 7,291,997 | 1.3043 → 6.1036 | 0.8091 → 5.1477 | 1.4392 |
| manual-valgrind | checker-bitmap-select | 30,924,288 | 14,905,493 | 1.3043 → 2.1255 | 0.8091 → 1.5679 | 1.0245 |
| manual-valgrind | checker-bitmap-xor-book | 30,924,288 | 6,527,085 | 1.3043 → 4.9093 | 0.8091 → 4.1685 | 1.0362 |
| manual-valgrind | checker-bitmap-xor-flat | 30,924,288 | 30,927,100 | 1.3043 → 1.0792 | 0.8091 → 0.6600 | 1.0793 |
| manual-valgrind | checker-bitmap-xor-hot | 30,924,288 | 5,689,159 | 1.3043 → 4.1315 | 0.8091 → 3.3168 | 0.7601 |
| manual-valgrind | checker-bitmap-xor-hotplanes | 30,924,288 | 5,689,159 | 1.3043 → 4.1314 | 0.8091 → 3.4003 | 0.7601 |
| manual-valgrind | checker-bitmap-xor-planes | 30,924,288 | 8,128,963 | 1.3043 → 3.4362 | 0.8091 → 2.3048 | 0.9033 |
| manual-valgrind | checker-bitmap-xor-tree | 30,924,288 | 8,128,963 | 1.3043 → 3.4361 | 0.8091 → 2.7195 | 0.9032 |
| modular-panels | modular-joint | 25,165,824 | 28,312,524 | 7.9918 → 1.6383 | 7.9873 → 1.2147 | 1.8432 |
| nci | lattice-rows-above | 33,553,445 | 33,554,761 | 2.4293 → 1.7313 | 1.9466 → 1.0145 | 1.7314 |
| nci | lattice-rows-columns | 33,553,445 | 33,554,761 | 2.4293 → 2.4775 | 1.9466 → 0.6467 | 2.4776 |
| nci | lattice-rows-delta | 33,553,445 | 33,554,761 | 2.4293 → 1.2887 | 1.9466 → 0.8982 | 1.2888 |
| nci | lattice-rows-field-positions | 33,553,445 | 33,619,633 | 2.4293 → 2.4463 | 1.9466 → 1.7480 | 2.4511 |
| nci | lattice-rows-field-prefix | 33,553,445 | 31,636,805 | 2.4293 → 2.6398 | 1.9466 → 1.9028 | 2.4890 |
| nci | lattice-rows-fields | 33,553,445 | 33,558,193 | 2.4293 → 2.4309 | 1.9466 → 1.9466 | 2.4313 |
| nci | lattice-rows-framed | 33,553,445 | 33,554,761 | 2.4293 → 2.4775 | 1.9466 → 1.8443 | 2.4776 |
| nci | lattice-rows-joint | 33,553,445 | 33,554,761 | 2.4293 → 1.2887 | 1.9466 → 0.7681 | 1.2888 |
| nci | lattice-rows-prefix | 33,553,445 | 31,633,221 | 2.4293 → 2.6393 | 1.9466 → 1.9022 | 2.4882 |
| nci | lattice-rows-route-select | 33,553,445 | 33,554,761 | 2.4293 → 2.5964 | 1.9466 → 0.6633 | 2.5965 |
| nci | lattice-rows-select | 33,553,445 | 33,554,761 | 2.4293 → 2.5964 | 1.9466 → 0.6633 | 2.5965 |
| nci-row-shuffled | lattice-rows-columns | 33,553,445 | 33,554,761 | 2.4293 → 2.4775 | 2.3190 → 2.1755 | 2.4776 |
| nci-row-shuffled | lattice-rows-delta | 33,553,445 | 33,554,761 | 2.4293 → 3.9131 | 2.3190 → 3.6970 | 3.9132 |
| nci-row-shuffled | lattice-rows-field-positions | 33,553,445 | 33,619,633 | 2.4293 → 2.4463 | 2.3190 → 2.3469 | 2.4511 |
| nci-row-shuffled | lattice-rows-field-prefix | 33,553,445 | 33,942,978 | 2.4293 → 2.5895 | 2.3190 → 2.3101 | 2.6195 |
| nci-row-shuffled | lattice-rows-fields | 33,553,445 | 33,558,193 | 2.4293 → 2.4309 | 2.3190 → 2.3189 | 2.4313 |
| nci-row-shuffled | lattice-rows-framed | 33,553,445 | 33,554,761 | 2.4293 → 2.4775 | 2.3190 → 2.1714 | 2.4776 |
| nci-row-shuffled | lattice-rows-joint | 33,553,445 | 33,554,761 | 2.4293 → 3.9131 | 2.3190 → 2.6379 | 3.9132 |
| nci-row-shuffled | lattice-rows-prefix | 33,553,445 | 33,939,394 | 2.4293 → 2.5891 | 2.3190 → 2.3095 | 2.6189 |
| nci-row-shuffled | lattice-rows-route-select | 33,553,445 | 33,554,761 | 2.4293 → 2.4775 | 2.3190 → 2.1755 | 2.4776 |
| nci-row-shuffled | lattice-rows-select | 33,553,445 | 33,554,761 | 2.4293 → 2.4775 | 2.3190 → 2.1755 | 2.4776 |
| noaa-1990-prefix | lattice-rows-above | 25,165,824 | 25,166,796 | 3.9764 → 2.1622 | 2.6846 → 1.4320 | 2.1623 |
| noaa-1990-prefix | lattice-rows-columns | 25,165,824 | 25,166,796 | 3.9764 → 4.0526 | 2.6846 → 1.0043 | 4.0528 |
| noaa-1990-prefix | lattice-rows-delta | 25,165,824 | 25,166,796 | 3.9764 → 1.5805 | 2.6846 → 1.0964 | 1.5805 |
| noaa-1990-prefix | lattice-rows-field-positions | 25,165,824 | 25,215,468 | 3.9764 → 3.9918 | 2.6846 → 0.9572 | 3.9997 |
| noaa-1990-prefix | lattice-rows-field-prefix | 25,165,824 | 15,572,584 | 3.9764 → 3.7762 | 2.6846 → 1.9335 | 2.3367 |
| noaa-1990-prefix | lattice-rows-fields | 25,165,824 | 25,169,388 | 3.9764 → 3.9783 | 2.6846 → 2.6957 | 3.9789 |
| noaa-1990-prefix | lattice-rows-framed | 25,165,824 | 25,166,796 | 3.9764 → 4.0526 | 2.6846 → 2.7191 | 4.0528 |
| noaa-1990-prefix | lattice-rows-joint | 25,165,824 | 25,166,796 | 3.9764 → 1.5805 | 2.6846 → 1.0309 | 1.5805 |
| noaa-1990-prefix | lattice-rows-literal | 25,165,824 | 25,166,316 | 3.9764 → 3.9767 | 2.6846 → 2.6847 | 3.9767 |
| noaa-1990-prefix | lattice-rows-positions | 25,165,824 | 25,172,460 | 3.9764 → 3.9796 | 2.6846 → 3.0985 | 3.9806 |
| noaa-1990-prefix | lattice-rows-prefix | 25,165,824 | 30,802,601 | 3.9764 → 3.9579 | 2.6846 → 2.2792 | 4.8444 |
| noaa-1990-prefix | lattice-rows-route-select | 25,165,824 | 25,176,534 | 3.9764 → 3.9859 | 2.6846 → 2.6750 | 3.9876 |
| noaa-1990-prefix | lattice-rows-select | 25,165,824 | 25,166,786 | 3.9764 → 4.1541 | 2.6846 → 1.1110 | 4.1543 |
| noaa-2020-prefix | lattice-rows-above | 25,165,824 | 25,166,796 | 3.9485 → 2.1309 | 2.8067 → 1.4288 | 2.1309 |
| noaa-2020-prefix | lattice-rows-columns | 25,165,824 | 25,166,796 | 3.9485 → 4.0258 | 2.8067 → 1.0384 | 4.0260 |
| noaa-2020-prefix | lattice-rows-delta | 25,165,824 | 25,166,796 | 3.9485 → 1.6280 | 2.8067 → 1.1176 | 1.6281 |
| noaa-2020-prefix | lattice-rows-field-positions | 25,165,824 | 25,215,468 | 3.9485 → 3.9639 | 2.8067 → 0.9553 | 3.9717 |
| noaa-2020-prefix | lattice-rows-field-prefix | 25,165,824 | 15,393,657 | 3.9485 → 3.8387 | 2.8067 → 2.0128 | 2.3481 |
| noaa-2020-prefix | lattice-rows-fields | 25,165,824 | 25,169,388 | 3.9485 → 3.9504 | 2.8067 → 2.8159 | 3.9510 |
| noaa-2020-prefix | lattice-rows-framed | 25,165,824 | 25,166,796 | 3.9485 → 4.0258 | 2.8067 → 2.8370 | 4.0260 |
| noaa-2020-prefix | lattice-rows-joint | 25,165,824 | 25,166,796 | 3.9485 → 1.6280 | 2.8067 → 1.0679 | 1.6281 |
| noaa-2020-prefix | lattice-rows-literal | 25,165,824 | 25,166,316 | 3.9485 → 3.9488 | 2.8067 → 2.8068 | 3.9489 |
| noaa-2020-prefix | lattice-rows-positions | 25,165,824 | 25,172,460 | 3.9485 → 3.9516 | 2.8067 → 3.2197 | 3.9527 |
| noaa-2020-prefix | lattice-rows-prefix | 25,165,824 | 30,783,066 | 3.9485 → 3.9139 | 2.8067 → 2.3761 | 4.7875 |
| noaa-2020-prefix | lattice-rows-route-select | 25,165,824 | 25,172,268 | 3.9485 → 3.9516 | 2.8067 → 2.8413 | 3.9526 |
| noaa-2020-prefix | lattice-rows-select | 25,165,824 | 25,166,796 | 3.9485 → 4.0258 | 2.8067 → 1.0384 | 4.0260 |
| noisy-spacetime | four-joint | 25,165,824 | 34,605,324 | 7.9645 → 3.2005 | 7.9554 → 2.0327 | 4.4010 |
| numerical | lattice-joint | 25,696,748 | 25,696,985 | 6.3494 → 4.9333 | 5.5271 → 3.7053 | 4.9333 |
| numerical | modular-joint | 25,696,748 | 25,697,750 | 6.3494 → 6.3493 | 5.5271 → 5.5270 | 6.3495 |
| rotated-stamps | checker-bitmap-direct-book | 28,311,552 | 4,786,724 | 2.1087 → 6.3996 | 1.5529 → 4.4591 | 1.0820 |
| rotated-stamps | checker-bitmap-direct-tree | 28,311,552 | 9,660,566 | 2.1087 → 5.1941 | 1.5529 → 2.3352 | 1.7723 |
| rotated-stamps | checker-bitmap-orbit-book | 28,311,552 | 10,109,056 | 2.1087 → 6.2687 | 1.5529 → 4.9895 | 2.2383 |
| rotated-stamps | checker-bitmap-rotated-book | 28,311,552 | 885,494 | 2.1087 → 6.9034 | 1.5529 → 5.3186 | 0.2159 |
| shared-orbit-1000 | pilot06-checker-3-fixed | 25,165,824 | 22,274,238 | 6.9648 → 7.7281 | 6.3175 → 7.4767 | 6.8401 |
| shuffled-witnesses | witness-joint | 22,630,320 | 19,790,312 | 2.9495 → 3.0670 | 2.7803 → 1.7457 | 2.6821 |
| uniform | checker-bitmap-direct-book | 25,165,824 | 31,977,556 | 8.0000 → 7.9274 | 7.9981 → 7.8311 | 10.0731 |
| uniform | checker-bitmap-orbit-book | 25,165,824 | 31,977,556 | 8.0000 → 7.9274 | 7.9981 → 7.8312 | 10.0731 |
| uniform | checker-bitmap-select | 25,165,824 | 25,168,884 | 8.0000 → 8.0000 | 7.9981 → 7.9980 | 8.0010 |
| uniform | checker-bitmap-xor-flat | 25,165,824 | 25,168,884 | 8.0000 → 8.0000 | 7.9981 → 7.9980 | 8.0010 |
| uniform | lattice-rows-joint | 25,165,824 | 25,312,096 | 8.0000 → 7.9964 | 7.9981 → 7.9819 | 8.0429 |
| uniform | lattice-rows-route-select | 25,165,824 | 25,166,316 | 8.0000 → 8.0000 | 7.9981 → 7.9981 | 8.0001 |
| uniform | lattice-rows-select | 25,165,824 | 25,166,316 | 8.0000 → 8.0000 | 7.9981 → 7.9981 | 8.0001 |
| uniform | modular-joint | 25,165,824 | 25,166,796 | 8.0000 → 8.0000 | 7.9981 → 7.9981 | 8.0003 |
| webster | lattice-rows-joint | 41,458,703 | 41,460,349 | 4.9707 → 6.7647 | 3.4171 → 5.8431 | 6.7650 |
| webster | lattice-rows-select | 41,458,703 | 41,459,510 | 4.9707 → 4.9710 | 3.4171 → 3.4171 | 4.9711 |
| whiteboard-witnesses | witness-joint | 22,630,320 | 14,110,128 | 2.9495 → 1.9285 | 2.7803 → 0.7663 | 1.2024 |
| wiki-transfer | lattice-rows-field-positions | 25,165,824 | 25,215,468 | 5.0850 → 5.0990 | 3.8807 → 4.3003 | 5.1090 |
| wiki-transfer | lattice-rows-field-prefix | 25,165,824 | 24,571,696 | 5.0850 → 5.1774 | 3.8807 → 3.8770 | 5.0552 |
| wiki-transfer | lattice-rows-fields | 25,165,824 | 25,169,388 | 5.0850 → 5.0863 | 3.8807 → 3.8892 | 5.0870 |
| wiki-transfer | lattice-rows-joint | 25,165,824 | 25,275,908 | 5.0850 → 6.2922 | 3.8807 → 5.3031 | 6.3197 |
| wiki-transfer | lattice-rows-prefix | 25,165,824 | 24,810,563 | 5.0850 → 5.1749 | 3.8807 → 3.8635 | 5.1019 |
| wiki-transfer | lattice-rows-route-select | 25,165,824 | 25,166,636 | 5.0850 → 5.0854 | 3.8807 → 3.8828 | 5.0855 |
| wiki-transfer | lattice-rows-select | 25,165,824 | 25,166,316 | 5.0850 → 5.0852 | 3.8807 → 3.8807 | 5.0853 |
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
| covertype-prefix | lattice-rows-field-positions | 3,997,073 → 2,493,345 (+37.621%) | 3,778,786 → 2,410,868 (+36.200%) | 2,801,076 → 1,816,048 (+35.166%) |
| covertype-prefix | lattice-rows-field-prefix | 3,997,073 → 3,365,027 (+15.813%) | 3,778,786 → 3,198,897 (+15.346%) | 2,801,076 → 2,283,648 (+18.472%) |
| covertype-prefix | lattice-rows-fields | 3,997,073 → 3,372,812 (+15.618%) | 3,778,786 → 3,279,530 (+13.212%) | 2,801,076 → 2,198,712 (+21.505%) |
| covertype-prefix | lattice-rows-joint | 3,997,073 → 3,422,678 (+14.370%) | 3,778,786 → 3,312,836 (+12.331%) | 2,801,076 → 2,742,460 (+2.093%) |
| covertype-prefix | lattice-rows-prefix | 3,997,073 → 4,185,009 (-4.702%) | 3,778,786 → 4,039,129 (-6.890%) | 2,801,076 → 2,966,092 (-5.891%) |
| evolved-stamps | checker-bitmap-direct-book | 9,210,659 → 2,654,150 (+71.184%) | 9,023,243 → 2,754,721 (+69.471%) | 7,530,660 → 2,120,388 (+71.843%) |
| evolved-stamps | checker-bitmap-direct-flat | 9,210,659 → 9,212,352 (-0.018%) | 9,023,243 → 9,024,278 (-0.011%) | 7,530,660 → 7,526,840 (+0.051%) |
| evolved-stamps | checker-bitmap-direct-tree | 9,210,659 → 2,700,418 (+70.682%) | 9,023,243 → 2,958,588 (+67.211%) | 7,530,660 → 1,975,876 (+73.762%) |
| evolved-stamps | checker-bitmap-orbit-book | 9,210,659 → 622,700 (+93.239%) | 9,023,243 → 623,735 (+93.087%) | 7,530,660 → 560,916 (+92.552%) |
| evolved-stamps | checker-bitmap-orbit-flat | 9,210,659 → 7,130,259 (+22.587%) | 9,023,243 → 6,884,881 (+23.698%) | 7,530,660 → 5,485,804 (+27.154%) |
| evolved-stamps | checker-bitmap-orbit-hot | 9,210,659 → 646,407 (+92.982%) | 9,023,243 → 653,696 (+92.755%) | 7,530,660 → 585,652 (+92.223%) |
| evolved-stamps | checker-bitmap-orbit-hotplanes | 9,210,659 → 766,811 (+91.675%) | 9,023,243 → 767,416 (+91.495%) | 7,530,660 → 693,544 (+90.790%) |
| evolved-stamps | checker-bitmap-orbit-planes | 9,210,659 → 3,534,488 (+61.626%) | 9,023,243 → 3,490,104 (+61.321%) | 7,530,660 → 3,076,668 (+59.145%) |
| evolved-stamps | checker-bitmap-orbit-tree | 9,210,659 → 807,400 (+91.234%) | 9,023,243 → 781,611 (+91.338%) | 7,530,660 → 628,356 (+91.656%) |
| evolved-stamps | checker-bitmap-rotated-book | 9,210,659 → 5,366,106 (+41.740%) | 9,023,243 → 5,577,984 (+38.182%) | 7,530,660 → 4,102,704 (+45.520%) |
| evolved-stamps | checker-bitmap-select | 9,210,659 → 622,700 (+93.239%) | 9,023,243 → 623,735 (+93.087%) | 7,530,660 → 560,916 (+92.552%) |
| evolved-stamps | checker-bitmap-xor-book | 9,210,659 → 2,823,988 (+69.340%) | 9,023,243 → 2,945,054 (+67.361%) | 7,530,660 → 2,275,564 (+69.783%) |
| evolved-stamps | checker-bitmap-xor-flat | 9,210,659 → 9,509,890 (-3.249%) | 9,023,243 → 9,322,938 (-3.321%) | 7,530,660 → 7,732,272 (-2.677%) |
| evolved-stamps | checker-bitmap-xor-tree | 9,210,659 → 2,784,689 (+69.767%) | 9,023,243 → 3,117,274 (+65.453%) | 7,530,660 → 2,084,084 (+72.325%) |
| formula-text | pilot11-dag | 4,118,040 → 2,187,854 (+46.871%) | 2,958,719 → 2,322,775 (+21.494%) | 1,856,404 → 1,625,172 (+12.456%) |
| graphs-shuffled-lines | checker-bitmap-direct-book | 1,849,713 → 3,606,684 (-94.986%) | 2,036,986 → 3,536,239 (-73.602%) | 1,380,120 → 2,771,044 (-100.783%) |
| graphs-shuffled-lines | checker-bitmap-direct-flat | 1,849,713 → 1,851,560 (-0.100%) | 2,036,986 → 2,039,106 (-0.104%) | 1,380,120 → 1,392,196 (-0.875%) |
| graphs-shuffled-lines | checker-bitmap-direct-tree | 1,849,713 → 2,826,361 (-52.800%) | 2,036,986 → 2,674,340 (-31.289%) | 1,380,120 → 1,991,168 (-44.275%) |
| graphs-shuffled-lines | checker-bitmap-orbit-book | 1,849,713 → 6,280,069 (-239.516%) | 2,036,986 → 6,223,539 (-205.527%) | 1,380,120 → 4,865,512 (-252.543%) |
| graphs-shuffled-lines | checker-bitmap-select | 1,849,713 → 1,851,560 (-0.100%) | 2,036,986 → 2,039,106 (-0.104%) | 1,380,120 → 1,392,196 (-0.875%) |
| graphs-shuffled-lines | checker-bitmap-xor-flat | 1,849,713 → 2,408,779 (-30.224%) | 2,036,986 → 2,576,199 (-26.471%) | 1,380,120 → 1,844,152 (-33.623%) |
| graphs-shuffled-lines | checker-bitmap-xor-hotplanes | 1,849,713 → 2,933,192 (-58.576%) | 2,036,986 → 3,010,554 (-47.795%) | 1,380,120 → 2,612,392 (-89.287%) |
| graphs-shuffled-lines | checker-bitmap-xor-tree | 1,849,713 → 3,492,995 (-88.840%) | 2,036,986 → 3,349,886 (-64.453%) | 1,380,120 → 2,593,716 (-87.934%) |
| hidden-products | shared-shared | 14,343,986 → 13,038,675 (+9.100%) | 14,118,577 → 13,077,821 (+7.372%) | 13,314,968 → 13,011,616 (+2.278%) |
| learned-field | learned-coupled | 29,389,440 → 11,276,527 (+61.631%) | 29,358,227 → 11,231,282 (+61.744%) | 29,419,328 → 10,497,028 (+64.319%) |
| luma-jake | learned-coupled | 1,716,540 → 1,796,738 (-4.672%) | 8,869,318 → 1,712,131 (+80.696%) | 990,504 → 1,375,752 (-38.894%) |
| manual-graphs | checker-bitmap-direct-book | 1,325,130 → 1,389,866 (-4.885%) | 1,520,849 → 1,464,931 (+3.677%) | 1,004,072 → 1,076,292 (-7.193%) |
| manual-graphs | checker-bitmap-direct-flat | 1,325,130 → 1,328,836 (-0.280%) | 1,520,849 → 1,523,258 (-0.158%) | 1,004,072 → 1,008,172 (-0.408%) |
| manual-graphs | checker-bitmap-direct-hot | 1,325,130 → 1,046,567 (+21.022%) | 1,520,849 → 1,139,557 (+25.071%) | 1,004,072 → 796,608 (+20.662%) |
| manual-graphs | checker-bitmap-direct-hotplanes | 1,325,130 → 1,314,345 (+0.814%) | 1,520,849 → 1,356,654 (+10.796%) | 1,004,072 → 1,106,104 (-10.162%) |
| manual-graphs | checker-bitmap-direct-planes | 1,325,130 → 1,252,966 (+5.446%) | 1,520,849 → 1,326,907 (+12.752%) | 1,004,072 → 995,652 (+0.839%) |
| manual-graphs | checker-bitmap-direct-tree | 1,325,130 → 926,450 (+30.086%) | 1,520,849 → 1,067,575 (+29.804%) | 1,004,072 → 634,084 (+36.849%) |
| manual-graphs | checker-bitmap-orbit-book | 1,325,130 → 1,818,834 (-37.257%) | 1,520,849 → 2,009,971 (-32.161%) | 1,004,072 → 1,403,424 (-39.773%) |
| manual-graphs | checker-bitmap-orbit-flat | 1,325,130 → 2,163,497 (-63.267%) | 1,520,849 → 2,368,383 (-55.728%) | 1,004,072 → 1,790,876 (-78.361%) |
| manual-graphs | checker-bitmap-orbit-tree | 1,325,130 → 1,249,242 (+5.727%) | 1,520,849 → 1,561,232 (-2.655%) | 1,004,072 → 868,944 (+13.458%) |
| manual-graphs | checker-bitmap-select | 1,325,130 → 970,779 (+26.741%) | 1,520,849 → 1,109,905 (+27.021%) | 1,004,072 → 690,144 (+31.265%) |
| manual-graphs | checker-bitmap-xor-book | 1,325,130 → 1,383,577 (-4.411%) | 1,520,849 → 1,479,231 (+2.736%) | 1,004,072 → 1,102,620 (-9.815%) |
| manual-graphs | checker-bitmap-xor-flat | 1,325,130 → 1,359,169 (-2.569%) | 1,520,849 → 1,513,711 (+0.469%) | 1,004,072 → 1,112,424 (-10.791%) |
| manual-graphs | checker-bitmap-xor-hot | 1,325,130 → 1,010,214 (+23.765%) | 1,520,849 → 1,125,042 (+26.025%) | 1,004,072 → 780,124 (+22.304%) |
| manual-graphs | checker-bitmap-xor-hotplanes | 1,325,130 → 1,273,925 (+3.864%) | 1,520,849 → 1,294,290 (+14.897%) | 1,004,072 → 1,135,300 (-13.070%) |
| manual-graphs | checker-bitmap-xor-planes | 1,325,130 → 1,201,823 (+9.305%) | 1,520,849 → 1,250,981 (+17.745%) | 1,004,072 → 1,020,492 (-1.635%) |
| manual-graphs | checker-bitmap-xor-tree | 1,325,130 → 883,342 (+33.339%) | 1,520,849 → 1,031,081 (+32.204%) | 1,004,072 → 612,788 (+38.970%) |
| manual-graphs | pilot07-pre-1 | 1,325,130 → 2,215,382 (-67.182%) | 1,520,849 → 2,217,323 (-45.795%) | 1,004,072 → 2,156,664 (-114.792%) |
| manual-library | checker-bitmap-direct-book | 1,903,362 → 1,891,562 (+0.620%) | 2,189,641 → 2,053,017 (+6.240%) | 1,375,968 → 1,420,104 (-3.208%) |
| manual-library | checker-bitmap-direct-tree | 1,903,362 → 1,219,247 (+35.942%) | 2,189,641 → 1,537,629 (+29.777%) | 1,375,968 → 739,252 (+46.274%) |
| manual-library | checker-bitmap-orbit-book | 1,903,362 → 2,422,699 (-27.285%) | 2,189,641 → 2,804,192 (-28.066%) | 1,375,968 → 1,787,632 (-29.918%) |
| manual-library | checker-bitmap-select | 1,903,362 → 1,260,597 (+33.770%) | 2,189,641 → 1,562,357 (+28.648%) | 1,375,968 → 804,356 (+41.543%) |
| manual-library | checker-bitmap-xor-book | 1,903,362 → 1,884,878 (+0.971%) | 2,189,641 → 2,069,896 (+5.469%) | 1,375,968 → 1,450,876 (-5.444%) |
| manual-library | checker-bitmap-xor-flat | 1,903,362 → 1,920,038 (-0.876%) | 2,189,641 → 2,172,094 (+0.801%) | 1,375,968 → 1,499,812 (-9.001%) |
| manual-library | checker-bitmap-xor-hot | 1,903,362 → 1,382,633 (+27.358%) | 2,189,641 → 1,610,206 (+26.463%) | 1,375,968 → 1,020,688 (+25.820%) |
| manual-library | checker-bitmap-xor-hotplanes | 1,903,362 → 1,854,681 (+2.558%) | 2,189,641 → 1,888,003 (+13.776%) | 1,375,968 → 1,635,116 (-18.834%) |
| manual-library | checker-bitmap-xor-planes | 1,903,362 → 1,745,729 (+8.282%) | 2,189,641 → 1,864,803 (+14.835%) | 1,375,968 → 1,417,244 (-3.000%) |
| manual-library | checker-bitmap-xor-tree | 1,903,362 → 1,162,886 (+38.904%) | 2,189,641 → 1,480,008 (+32.409%) | 1,375,968 → 717,328 (+47.867%) |
| manual-transfer | checker-bitmap-direct-book | 2,005,044 → 2,061,438 (-2.813%) | 2,229,879 → 2,196,335 (+1.504%) | 1,468,704 → 1,534,596 (-4.486%) |
| manual-transfer | checker-bitmap-direct-tree | 2,005,044 → 1,360,567 (+32.143%) | 2,229,879 → 1,597,548 (+28.357%) | 1,468,704 → 801,760 (+45.410%) |
| manual-transfer | checker-bitmap-orbit-book | 2,005,044 → 2,604,989 (-29.922%) | 2,229,879 → 2,946,901 (-32.155%) | 1,468,704 → 1,924,348 (-31.024%) |
| manual-transfer | checker-bitmap-select | 2,005,044 → 1,495,485 (+25.414%) | 2,229,879 → 1,719,298 (+22.897%) | 1,468,704 → 973,176 (+33.739%) |
| manual-transfer | checker-bitmap-xor-book | 2,005,044 → 2,025,025 (-0.997%) | 2,229,879 → 2,170,895 (+2.645%) | 1,468,704 → 1,551,548 (-5.641%) |
| manual-transfer | checker-bitmap-xor-flat | 2,005,044 → 1,992,156 (+0.643%) | 2,229,879 → 2,217,736 (+0.545%) | 1,468,704 → 1,566,396 (-6.652%) |
| manual-transfer | checker-bitmap-xor-hot | 2,005,044 → 1,534,895 (+23.448%) | 2,229,879 → 1,701,213 (+23.708%) | 1,468,704 → 1,142,092 (+22.238%) |
| manual-transfer | checker-bitmap-xor-hotplanes | 2,005,044 → 2,023,740 (-0.932%) | 2,229,879 → 2,029,164 (+9.001%) | 1,468,704 → 1,783,448 (-21.430%) |
| manual-transfer | checker-bitmap-xor-planes | 2,005,044 → 1,847,808 (+7.842%) | 2,229,879 → 1,935,600 (+13.197%) | 1,468,704 → 1,511,756 (-2.931%) |
| manual-transfer | checker-bitmap-xor-tree | 2,005,044 → 1,307,011 (+34.814%) | 2,229,879 → 1,508,593 (+32.346%) | 1,468,704 → 774,040 (+47.298%) |
| manual-valgrind | checker-bitmap-direct-book | 2,582,180 → 2,769,522 (-7.255%) | 2,943,798 → 3,005,449 (-2.094%) | 1,908,720 → 2,038,308 (-6.789%) |
| manual-valgrind | checker-bitmap-direct-tree | 2,582,180 → 1,787,822 (+30.763%) | 2,943,798 → 2,242,189 (+23.833%) | 1,908,720 → 1,042,068 (+45.405%) |
| manual-valgrind | checker-bitmap-orbit-book | 2,582,180 → 3,568,565 (-38.200%) | 2,943,798 → 4,095,977 (-39.139%) | 1,908,720 → 2,574,776 (-34.895%) |
| manual-valgrind | checker-bitmap-select | 2,582,180 → 2,003,009 (+22.430%) | 2,943,798 → 2,412,096 (+18.062%) | 1,908,720 → 1,298,608 (+31.964%) |
| manual-valgrind | checker-bitmap-xor-book | 2,582,180 → 2,790,503 (-8.068%) | 2,943,798 → 3,044,802 (-3.431%) | 1,908,720 → 2,106,880 (-10.382%) |
| manual-valgrind | checker-bitmap-xor-flat | 2,582,180 → 2,683,089 (-3.908%) | 2,943,798 → 3,014,259 (-2.394%) | 1,908,720 → 2,112,440 (-10.673%) |
| manual-valgrind | checker-bitmap-xor-hot | 2,582,180 → 2,042,660 (+20.894%) | 2,943,798 → 2,347,526 (+20.255%) | 1,908,720 → 1,462,128 (+23.397%) |
| manual-valgrind | checker-bitmap-xor-hotplanes | 2,582,180 → 2,689,270 (-4.147%) | 2,943,798 → 2,732,444 (+7.180%) | 1,908,720 → 2,369,924 (-24.163%) |
| manual-valgrind | checker-bitmap-xor-planes | 2,582,180 → 2,506,790 (+2.920%) | 2,943,798 → 2,690,298 (+8.611%) | 1,908,720 → 1,998,760 (-4.717%) |
| manual-valgrind | checker-bitmap-xor-tree | 2,582,180 → 1,738,730 (+32.664%) | 2,943,798 → 2,181,871 (+25.882%) | 1,908,720 → 1,025,524 (+46.272%) |
| modular-panels | modular-joint | 25,166,413 → 4,478,573 (+82.204%) | 25,168,569 → 4,695,964 (+81.342%) | 25,167,132 → 4,327,872 (+82.803%) |
| nci | lattice-rows-above | 2,835,396 → 3,218,569 (-13.514%) | 3,199,449 → 3,558,372 (-11.218%) | 1,779,272 → 2,070,980 (-16.395%) |
| nci | lattice-rows-columns | 2,835,396 → 2,489,621 (+12.195%) | 3,199,449 → 2,363,037 (+26.142%) | 1,779,272 → 1,872,004 (-5.212%) |
| nci | lattice-rows-delta | 2,835,396 → 3,259,904 (-14.972%) | 3,199,449 → 3,513,161 (-9.805%) | 1,779,272 → 2,167,976 (-21.846%) |
| nci | lattice-rows-field-positions | 2,835,396 → 3,183,691 (-12.284%) | 3,199,449 → 2,944,428 (+7.971%) | 1,779,272 → 2,243,240 (-26.076%) |
| nci | lattice-rows-field-prefix | 2,835,396 → 2,943,388 (-3.809%) | 3,199,449 → 3,141,871 (+1.800%) | 1,779,272 → 1,770,816 (+0.475%) |
| nci | lattice-rows-fields | 2,835,396 → 2,836,967 (-0.055%) | 3,199,449 → 3,201,668 (-0.069%) | 1,779,272 → 1,780,856 (-0.089%) |
| nci | lattice-rows-framed | 2,835,396 → 2,897,093 (-2.176%) | 3,199,449 → 3,254,607 (-1.724%) | 1,779,272 → 1,811,796 (-1.828%) |
| nci | lattice-rows-joint | 2,835,396 → 2,761,194 (+2.617%) | 3,199,449 → 2,710,424 (+15.285%) | 1,779,272 → 2,126,876 (-19.536%) |
| nci | lattice-rows-prefix | 2,835,396 → 2,942,762 (-3.787%) | 3,199,449 → 3,141,513 (+1.811%) | 1,779,272 → 1,770,432 (+0.497%) |
| nci | lattice-rows-route-select | 2,835,396 → 2,483,811 (+12.400%) | 3,199,449 → 2,375,281 (+25.760%) | 1,779,272 → 1,866,432 (-4.899%) |
| nci | lattice-rows-select | 2,835,396 → 2,483,811 (+12.400%) | 3,199,449 → 2,375,281 (+25.760%) | 1,779,272 → 1,866,432 (-4.899%) |
| nci-row-shuffled | lattice-rows-columns | 12,578,509 → 11,833,316 (+5.924%) | 12,395,907 → 11,476,737 (+7.415%) | 10,671,000 → 9,958,468 (+6.677%) |
| nci-row-shuffled | lattice-rows-delta | 12,578,509 → 18,077,269 (-43.716%) | 12,395,907 → 18,304,913 (-47.669%) | 10,671,000 → 16,246,772 (-52.252%) |
| nci-row-shuffled | lattice-rows-field-positions | 12,578,509 → 12,691,175 (-0.896%) | 12,395,907 → 12,374,847 (+0.170%) | 10,671,000 → 10,804,532 (-1.251%) |
| nci-row-shuffled | lattice-rows-field-prefix | 12,578,509 → 12,812,624 (-1.861%) | 12,395,907 → 12,627,602 (-1.869%) | 10,671,000 → 10,796,956 (-1.180%) |
| nci-row-shuffled | lattice-rows-fields | 12,578,509 → 12,579,574 (-0.008%) | 12,395,907 → 12,398,506 (-0.021%) | 10,671,000 → 10,672,884 (-0.018%) |
| nci-row-shuffled | lattice-rows-framed | 12,578,509 → 11,915,614 (+5.270%) | 12,395,907 → 11,731,819 (+5.357%) | 10,671,000 → 10,081,648 (+5.523%) |
| nci-row-shuffled | lattice-rows-joint | 12,578,509 → 13,578,836 (-7.953%) | 12,395,907 → 13,695,892 (-10.487%) | 10,671,000 → 11,270,408 (-5.617%) |
| nci-row-shuffled | lattice-rows-prefix | 12,578,509 → 12,811,858 (-1.855%) | 12,395,907 → 12,627,056 (-1.865%) | 10,671,000 → 10,795,476 (-1.166%) |
| nci-row-shuffled | lattice-rows-route-select | 12,578,509 → 11,833,316 (+5.924%) | 12,395,907 → 11,476,737 (+7.415%) | 10,671,000 → 9,958,468 (+6.677%) |
| nci-row-shuffled | lattice-rows-select | 12,578,509 → 11,833,316 (+5.924%) | 12,395,907 → 11,476,737 (+7.415%) | 10,671,000 → 9,958,468 (+6.677%) |
| noaa-1990-prefix | lattice-rows-above | 3,541,939 → 3,343,075 (+5.615%) | 3,222,875 → 3,242,863 (-0.620%) | 1,816,516 → 1,956,820 (-7.724%) |
| noaa-1990-prefix | lattice-rows-columns | 3,541,939 → 3,221,769 (+9.039%) | 3,222,875 → 2,876,387 (+10.751%) | 1,816,516 → 2,273,628 (-25.164%) |
| noaa-1990-prefix | lattice-rows-delta | 3,541,939 → 3,835,972 (-8.301%) | 3,222,875 → 3,572,013 (-10.833%) | 1,816,516 → 2,262,664 (-24.561%) |
| noaa-1990-prefix | lattice-rows-field-positions | 3,541,939 → 2,307,035 (+34.865%) | 3,222,875 → 2,001,710 (+37.891%) | 1,816,516 → 1,276,732 (+29.715%) |
| noaa-1990-prefix | lattice-rows-field-prefix | 3,541,939 → 1,870,761 (+47.183%) | 3,222,875 → 1,705,482 (+47.082%) | 1,816,516 → 994,236 (+45.267%) |
| noaa-1990-prefix | lattice-rows-fields | 3,541,939 → 2,086,007 (+41.106%) | 3,222,875 → 1,913,577 (+40.625%) | 1,816,516 → 957,348 (+47.298%) |
| noaa-1990-prefix | lattice-rows-framed | 3,541,939 → 3,744,492 (-5.719%) | 3,222,875 → 3,456,834 (-7.259%) | 1,816,516 → 1,992,436 (-9.684%) |
| noaa-1990-prefix | lattice-rows-joint | 3,541,939 → 3,402,507 (+3.937%) | 3,222,875 → 3,209,091 (+0.428%) | 1,816,516 → 2,564,352 (-41.169%) |
| noaa-1990-prefix | lattice-rows-literal | 3,541,939 → 3,542,684 (-0.021%) | 3,222,875 → 3,223,895 (-0.032%) | 1,816,516 → 1,818,896 (-0.131%) |
| noaa-1990-prefix | lattice-rows-positions | 3,541,939 → 3,164,406 (+10.659%) | 3,222,875 → 2,655,397 (+17.608%) | 1,816,516 → 1,691,612 (+6.876%) |
| noaa-1990-prefix | lattice-rows-prefix | 3,541,939 → 3,784,147 (-6.838%) | 3,222,875 → 3,354,183 (-4.074%) | 1,816,516 → 1,882,168 (-3.614%) |
| noaa-1990-prefix | lattice-rows-route-select | 3,541,939 → 2,032,120 (+42.627%) | 3,222,875 → 1,852,984 (+42.505%) | 1,816,516 → 1,043,020 (+42.581%) |
| noaa-1990-prefix | lattice-rows-select | 3,541,939 → 3,216,603 (+9.185%) | 3,222,875 → 2,891,968 (+10.267%) | 1,816,516 → 2,261,252 (-24.483%) |
| noaa-2020-prefix | lattice-rows-above | 3,552,108 → 3,517,969 (+0.961%) | 3,271,833 → 3,360,252 (-2.702%) | 1,854,284 → 2,033,280 (-9.653%) |
| noaa-2020-prefix | lattice-rows-columns | 3,552,108 → 3,292,962 (+7.296%) | 3,271,833 → 2,943,377 (+10.039%) | 1,854,284 → 2,344,304 (-26.426%) |
| noaa-2020-prefix | lattice-rows-delta | 3,552,108 → 3,888,816 (-9.479%) | 3,271,833 → 3,618,964 (-10.610%) | 1,854,284 → 2,252,304 (-21.465%) |
| noaa-2020-prefix | lattice-rows-field-positions | 3,552,108 → 2,364,895 (+33.423%) | 3,271,833 → 2,081,857 (+36.370%) | 1,854,284 → 1,466,456 (+20.915%) |
| noaa-2020-prefix | lattice-rows-field-prefix | 3,552,108 → 2,012,489 (+43.344%) | 3,271,833 → 1,767,719 (+45.972%) | 1,854,284 → 1,095,256 (+40.934%) |
| noaa-2020-prefix | lattice-rows-fields | 3,552,108 → 2,100,930 (+40.854%) | 3,271,833 → 1,917,471 (+41.395%) | 1,854,284 → 1,065,376 (+42.545%) |
| noaa-2020-prefix | lattice-rows-framed | 3,552,108 → 3,741,542 (-5.333%) | 3,271,833 → 3,477,930 (-6.299%) | 1,854,284 → 2,017,200 (-8.786%) |
| noaa-2020-prefix | lattice-rows-joint | 3,552,108 → 3,474,417 (+2.187%) | 3,271,833 → 3,272,224 (-0.012%) | 1,854,284 → 2,643,928 (-42.585%) |
| noaa-2020-prefix | lattice-rows-literal | 3,552,108 → 3,552,823 (-0.020%) | 3,271,833 → 3,272,923 (-0.033%) | 1,854,284 → 1,855,884 (-0.086%) |
| noaa-2020-prefix | lattice-rows-positions | 3,552,108 → 3,322,140 (+6.474%) | 3,271,833 → 2,800,785 (+14.397%) | 1,854,284 → 1,852,440 (+0.099%) |
| noaa-2020-prefix | lattice-rows-prefix | 3,552,108 → 3,763,027 (-5.938%) | 3,271,833 → 3,393,947 (-3.732%) | 1,854,284 → 1,917,724 (-3.421%) |
| noaa-2020-prefix | lattice-rows-route-select | 3,552,108 → 2,085,342 (+41.293%) | 3,271,833 → 1,909,412 (+41.641%) | 1,854,284 → 1,098,844 (+40.740%) |
| noaa-2020-prefix | lattice-rows-select | 3,552,108 → 3,292,962 (+7.296%) | 3,271,833 → 2,943,377 (+10.039%) | 1,854,284 → 2,344,304 (-26.426%) |
| noisy-spacetime | four-joint | 25,166,413 → 9,397,974 (+62.657%) | 25,042,968 → 9,362,367 (+62.615%) | 25,063,412 → 8,109,204 (+67.645%) |
| numerical | lattice-joint | 15,163,679 → 11,635,203 (+23.269%) | 15,063,439 → 11,486,297 (+23.747%) | 11,665,916 → 10,449,384 (+10.428%) |
| numerical | modular-joint | 15,163,679 → 15,164,986 (-0.009%) | 15,063,439 → 15,063,384 (+0.000%) | 11,665,916 → 11,730,228 (-0.551%) |
| rotated-stamps | checker-bitmap-direct-book | 7,867,492 → 2,244,509 (+71.471%) | 7,665,858 → 2,246,196 (+70.699%) | 5,962,732 → 1,700,168 (+71.487%) |
| rotated-stamps | checker-bitmap-direct-tree | 7,867,492 → 2,059,413 (+73.824%) | 7,665,858 → 2,116,004 (+72.397%) | 5,962,732 → 1,218,712 (+79.561%) |
| rotated-stamps | checker-bitmap-orbit-book | 7,867,492 → 5,441,366 (+30.837%) | 7,665,858 → 5,673,107 (+25.995%) | 5,962,732 → 4,136,800 (+30.622%) |
| rotated-stamps | checker-bitmap-rotated-book | 7,867,492 → 622,584 (+92.087%) | 7,665,858 → 623,741 (+91.863%) | 5,962,732 → 560,832 (+90.594%) |
| shared-orbit-1000 | pilot06-checker-3-fixed | 21,987,747 → 21,474,587 (+2.334%) | 22,067,549 → 21,470,554 (+2.705%) | 20,184,408 → 20,716,428 (-2.636%) |
| shuffled-witnesses | witness-joint | 6,474,999 → 3,768,334 (+41.802%) | 6,460,681 → 3,776,913 (+41.540%) | 4,322,840 → 3,550,292 (+17.871%) |
| uniform | checker-bitmap-direct-book | 25,166,413 → 31,103,267 (-23.590%) | 25,169,682 → 31,231,293 (-24.083%) | 25,167,136 → 30,331,704 (-20.521%) |
| uniform | checker-bitmap-orbit-book | 25,166,413 → 31,104,010 (-23.593%) | 25,169,682 → 31,231,950 (-24.086%) | 25,167,136 → 30,346,228 (-20.579%) |
| uniform | checker-bitmap-select | 25,166,413 → 25,168,724 (-0.009%) | 25,169,682 → 25,172,017 (-0.009%) | 25,167,136 → 25,169,704 (-0.010%) |
| uniform | checker-bitmap-xor-flat | 25,166,413 → 25,168,941 (-0.010%) | 25,169,682 → 25,172,234 (-0.010%) | 25,167,136 → 25,169,932 (-0.011%) |
| uniform | lattice-rows-joint | 25,166,413 → 25,312,688 (-0.581%) | 25,169,682 → 25,258,810 (-0.354%) | 25,167,136 → 25,300,180 (-0.529%) |
| uniform | lattice-rows-route-select | 25,166,413 → 25,166,905 (-0.002%) | 25,169,682 → 25,170,174 (-0.002%) | 25,167,136 → 25,167,628 (-0.002%) |
| uniform | lattice-rows-select | 25,166,413 → 25,166,905 (-0.002%) | 25,169,682 → 25,170,174 (-0.002%) | 25,167,136 → 25,167,628 (-0.002%) |
| uniform | modular-joint | 25,166,413 → 25,167,385 (-0.004%) | 25,169,682 → 25,170,654 (-0.004%) | 25,167,136 → 25,168,108 (-0.004%) |
| webster | lattice-rows-joint | 12,107,194 → 34,326,394 (-183.521%) | 12,201,972 → 34,381,121 (-181.767%) | 8,628,848 → 31,185,636 (-261.411%) |
| webster | lattice-rows-select | 12,107,194 → 12,109,357 (-0.018%) | 12,201,972 → 12,204,071 (-0.017%) | 8,628,848 → 8,629,872 (-0.012%) |
| whiteboard-witnesses | witness-joint | 4,602,354 → 1,109,554 (+75.892%) | 5,230,942 → 1,122,203 (+78.547%) | 2,968,412 → 961,108 (+67.622%) |
| wiki-transfer | lattice-rows-field-positions | 8,968,455 → 11,111,894 (-23.900%) | 9,232,082 → 11,665,311 (-26.356%) | 6,743,812 → 8,923,908 (-32.327%) |
| wiki-transfer | lattice-rows-field-prefix | 8,968,455 → 9,262,307 (-3.277%) | 9,232,082 → 9,809,440 (-6.254%) | 6,743,812 → 6,962,968 (-3.250%) |
| wiki-transfer | lattice-rows-fields | 8,968,455 → 9,166,657 (-2.210%) | 9,232,082 → 9,753,222 (-5.645%) | 6,743,812 → 6,908,720 (-2.445%) |
| wiki-transfer | lattice-rows-joint | 8,968,455 → 15,754,527 (-75.666%) | 9,232,082 → 16,107,898 (-74.477%) | 6,743,812 → 13,236,764 (-96.280%) |
| wiki-transfer | lattice-rows-prefix | 8,968,455 → 9,089,552 (-1.350%) | 9,232,082 → 9,339,483 (-1.163%) | 6,743,812 → 6,824,684 (-1.199%) |
| wiki-transfer | lattice-rows-route-select | 8,968,455 → 8,987,947 (-0.217%) | 9,232,082 → 9,268,308 (-0.392%) | 6,743,812 → 6,763,280 (-0.289%) |
| wiki-transfer | lattice-rows-select | 8,968,455 → 8,968,995 (-0.006%) | 9,232,082 → 9,233,599 (-0.016%) | 6,743,812 → 6,744,120 (-0.005%) |
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

The numbered pilots here already emit a reversible record stream. The adapter preserves the encoder’s block choices. For block-compressed formats it removes the terminal Zstandard frames and updates their lengths. For row and bitmap profiles it removes the outer Zstandard wrapper and measures the complete RGP1 or CBP1 stream. On restore it supplies the framing expected by the corresponding decoder. All backends receive the same frozen representation, including the modes selected by the original encoder’s internal cost model. These observations cover the listed profiles and inputs.

The [machine-readable receipts](preprocessing.jsonl) give the complete input, prepared and compressed stream hashes, commands, versions and byte counts. The [corpus manifest and preparation instructions](../README.md#inputs) describe their provenance.
