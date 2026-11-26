# M1 results (2026-11-21)

Plain grammar + GLZ inline definitions + frequency-class/uniform-index coding. Production cost 6.0. All round trips verified (SHA-256).

## enwik8

| | bytes |
|---|---|
| **statico M1** | **26,346,968** |
| xz (LTCB best settings) | 24,703,772 |
| xz (our run, dict 128 MiB) | 24,766,840 |
| GLZA 0.12 | 20,068,917 |
| statico M0 (order-0) | 61,862,699 |

M1 is +6.7% vs xz: below the 27 MB stop line, above the M1 target. Compress 294 s CPU, 2.9 GB peak RSS. Decompress 2.46 s (40.7 MB/s incl. SHA-256 check), 144 MB RSS: under the 50 MB/s goal (enforced from M3).

Grammar: 553,204 rules, main sequence 11,836,477 symbols, 1,435,125 body symbols, 94 rounds.

## silesia (xz = `xz -9e -T1`, our run)

| file | bytes | statico | xz | vs xz | comp s | dec MB/s |
|---|---:|---:|---:|---:|---:|---:|
| dickens | 10,192,446 | 2,780,136 | 2,831,212 | -1.8% | 23 | 53.5 |
| mozilla | 51,220,480 | 18,460,793 | 13,376,240 | +38.0% | 399 | 73.3 |
| mr | 9,970,564 | 3,219,062 | 2,751,892 | +17.0% | 50 | 95.2 |
| nci | 33,553,445 | 1,686,759 | 1,449,272 | +16.4% | 27 | 193.2 |
| ooffice | 6,152,192 | 2,958,153 | 2,427,224 | +21.9% | 14 | 66.8 |
| osdb | 10,085,684 | 2,723,344 | 2,844,556 | -4.3% | 10 | 110.1 |
| reymont | 6,627,202 | 1,369,204 | 1,315,592 | +4.1% | 7 | 106.9 |
| samba | 21,606,400 | 4,760,025 | 3,739,524 | +27.3% | 39 | 114.8 |
| sao | 7,251,944 | 5,059,448 | 4,425,664 | +14.3% | 38 | 59.9 |
| webster | 41,458,703 | 8,441,640 | 8,368,672 | +0.9% | 62 | 99.7 |
| x-ray | 8,474,240 | 5,661,172 | 4,491,264 | +26.0% | 24 | 62.7 |
| xml | 5,345,280 | 496,440 | 434,892 | +14.2% | 3 | 133.6 |

Text is close to xz (dickens −1.8%, webster +0.9%); binaries are far behind (no shape/record modelling yet: M5).
