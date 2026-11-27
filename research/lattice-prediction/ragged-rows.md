# What is the right column in a variable-width file?

On a 24 MiB sample of NOAA weather observations, subtracting the byte in the same column of the previous equal-width row made byte entropy fall from **3.949 to 1.628 bits per byte**. Zstandard level 3 then took **9.48% more space**. Gathering the station IDs together, the dates together, and so on left byte entropy at **3.950**, yet Zstandard took **40.85% less space**. The choice of which bytes become neighbors matters to the backend. [Paired measurements and hashes](../large-scale/results/preprocessing.md)

## The original experiment

The local program `lab/shape/ragged.c` asked if knowing the byte directly above a position helps predict the next byte in a variable-length line. Its driver saved results for a Canterbury text and Silesia XML. The table gives the lowest sequential prediction cost across the three recorded smoothing parameters, in bits per original byte. Each prediction used only earlier observations. [Historical file inventory](../evidence/protocol-index.tsv)

| Historical input | Bytes | Previous byte | Previous byte and byte above |
|---|---:|---:|---:|
| Canterbury `lcet10.txt` | 426,754 | 3.538 | 3.882 |
| Silesia XML | 5,345,280 | 3.494 | 3.244 |

Those small trials measured model cost. The new experiment builds an actual inverse, charges the row lengths and field boundaries, and passes the prepared stream to three compressors. The adjacent-row subtraction borrows the arithmetic of PNG's Up filter. The original lab's `tlvcols.py` provided another lead by examining distributions at structural positions. Column-oriented databases and XMill give precedents for storing like fields together. Work on sorting tables also shows how row order affects compression. Here the decoder recovers the exact input order, including delimiters and incomplete records. [PNG filtering, Table 11](https://www.w3.org/TR/png-3/) · [C-Store](https://people.csail.mit.edu/edmond/research/cstore/cstore.pdf) · [XMill](https://homes.cs.washington.edu/~suciu/XMILL/) · [Lemire, Kaser and Gutarra](https://arxiv.org/abs/1207.2189)

## What the decoder receives

The `RGP1` stream contains the original size followed by blocks covering up to 256 KiB of original bytes. Each block carries a one-byte mode and a four-byte payload length. All predictors reset at the block boundary, even in the middle of a record. The standalone `RGR1` archive wraps this representation with Zstandard. The paired benchmark sends the same complete RGP1 representation to each external backend. [Encoder and decoder](ragged.py) · [Field transforms](field_lanes.cpp)

| Profile suffix | Reversible operation |
|---|---|
| `literal`, `framed` | Copy the block, or split on LF and store lengths in original order followed by concatenated row bodies. Lengths 255 and above get a four-byte extension. |
| `above`, `delta` | Subtract the byte above modulo 256, using either the immediately preceding row or the most recent row of exactly the same width. The adjacent-row version can also predict from the preceding LF. |
| `columns`, `joint` | Group equal-width rows stably and emit their columns. The joint version first differences each group down the column. The length stream lets the decoder return each row to its original position. |
| `fields`, `positions`, `field-positions` | Group bytes by comma-delimited field number, byte position within the field, or both. The last of eight fields and last of sixteen positions absorb overflow. Each lane costs a four-byte length. |
| `prefix`, `field-prefix` | For each token write its common-prefix length with the previous token in its lane as an unsigned variable-length integer, then the suffix and original delimiter. Use one lane or eight field lanes. |
| `select`, `route-select` | Choose the smallest Zstandard-3 block among the six literal and row modes, or among those six plus the three field/position modes. The prefix variants are separate trials. |

For example, `aa,10\nb,2` becomes two nonempty field lanes, `aa,b,` and `10\n2`. The decoder starts in the first lane. Reading a comma advances it to the next field and reading LF brings it back to the first. Quotes, CR, NUL, extra commas, and a final record without LF survive unchanged. The prefix variant applies the front-coding principle directly to successive tokens in input order. [Front coding in Brisaboa et al., §2.1.3](https://users.dcc.uchile.cl/~gnavarro/ps/cikm19.pdf)

## Which changes paid for themselves?

Across eight inputs, 64 input/profile pairs went through gzip 6, Zstandard 3 and XZ 6. Each pair passed a byte-for-byte comparison after inverse preprocessing. Raw inputs range from 24 MiB to the 41,458,703-byte Webster file.

Each weather input contains the first 25,165,824 uncompressed bytes of a different year in the same archive series. NOAA records station, date, element, value, flags and observation time in successive fields. The 1990 sample tests transfer to a second year under the same schema. Every percentage below compares the compressed prepared stream with the **same backend on raw bytes**. Positive values mean smaller files. H0 describes byte frequencies and H1 conditions on the preceding byte. Both are measured on the complete prepared stream, including metadata. [NOAA field definitions](https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme-by_year.txt) · [Exact sizes and commands](../large-scale/results/preprocessing.jsonl)

| 2020 representation | Prepared bytes | H0 | H1 | gzip 6 saved | Zstd 3 saved | XZ 6 saved |
|---|---:|---:|---:|---:|---:|---:|
| Raw | 25,165,824 | 3.949 | 2.807 | — | — | — |
| Literal with block headers | 25,166,316 | 3.949 | 2.807 | -0.03% | -0.02% | -0.09% |
| Equal-width differences | 25,166,796 | 1.628 | 1.118 | -10.61% | -9.48% | -21.46% |
| Equal-width differences and columns | 25,166,796 | 1.628 | 1.068 | -0.01% | +2.19% | -42.58% |
| Field and position | 25,215,468 | 3.964 | 0.955 | +36.37% | +33.42% | +20.92% |
| One token lane with prefixes | 30,783,066 | 3.914 | 2.376 | -3.73% | -5.94% | -3.42% |
| Eight field lanes | 25,169,388 | 3.950 | 2.816 | +41.39% | +40.85% | +42.55% |
| Eight field lanes with prefixes | 15,393,657 | 3.839 | 2.013 | +45.97% | +43.34% | +40.93% |

The eight field lanes added just **3,564 bytes** to the 2020 input. The field-prefix representation removed **9,772,167 bytes** before compression. Turning on prefix coding without separating fields made all three archives larger. The field-prefix combination gave the best gzip and Zstandard results among these fixed variants in both years. XZ did better with field routing alone. In 1990 field routing saved **40.63% / 41.11% / 47.30%** with gzip / Zstandard / XZ. Field-prefix coding saved **47.08% / 47.18% / 45.27%** respectively.

## Does the weather result transfer to another table?

We applied five fixed profiles unchanged to the first 24 MiB of Jock Blackard’s Covertype dataset. Each record contains 54 terrain or categorical features and a cover-type label. The eight-field router places fields eight through 55 in the final lane. This makes Covertype a test of what the weather configuration can do on a wider schema. [UCI dataset and field definitions](https://archive.ics.uci.edu/dataset/31/covertype)

| Covertype representation | H0 | H1 | gzip 6 saved | Zstd 3 saved | XZ 6 saved |
|---|---:|---:|---:|---:|---:|
| Raw | 2.284 | 1.330 | — | — | — |
| Fields | 2.287 | 1.330 | +13.21% | +15.62% | +21.50% |
| Fields with prefixes | 2.533 | 1.271 | +15.35% | +15.81% | +18.47% |
| Field and position | 2.303 | 1.067 | +36.20% | +37.62% | +35.17% |

Separating byte positions was the strongest of these five variants on Covertype for all three backends. Prefix coding alone again grew the Zstandard result, here by 4.70%. A fixed-profile win on the weather schema did not predict the best layout on this table.

## What a byte histogram misses

A bounded match probe samples every 97th byte. It finds the most recent occurrence of the same four-byte prefix within 32 KiB and measures the exact match up to 64 bytes. A different compressor can choose a different match, look farther back, or encode literals at a different price. This probe measures one property of the byte order. [Probe implementation](match_probe.py) · [All probe counts and stream hashes](../large-scale/results/row-matches.jsonl)

| 2020 representation | Samples matching at least 16 bytes | Samples matching all 64 bytes |
|---|---:|---:|
| Raw | 35.8% | 0.0% |
| Fields | 65.5% | 41.2% |
| Field and position | 69.2% | 59.4% |
| Equal-width differences and columns | 64.1% | 53.5% |

Field routing preserved the payload histogram exactly and made long repeats common. Splitting fields again by position yielded even more long matches, yet saved fewer compressed bytes. The sampled matches describe an important change in the stream and cannot by themselves rank the transforms.

On the full 33,553,445-byte Silesia NCI file, column transposition alone saved **12.19%** with Zstandard. Adding vertical subtraction reduced the saving to **2.62%**. Shuffling bytes independently within each line fragment preserved its byte counts, width and LF position. On this control the combined transform **grew the Zstandard archive by 7.95%**. On the disjoint Wikipedia sample it grew the archive by **75.67%**, and on Webster by **183.52%**. The row selector stayed within **0.03%** of direct Zstandard on both prose inputs and on uniform random bytes. [All individual trials](../large-scale/results/preprocessing.md)

## Reproduce the weather comparison

From the repository root, build the field helper and obtain the pinned weather prefix. NOAA revises the yearly files. The manifest records both downloaded range hashes, timestamps and raw hashes. The input builder checks the raw hash before writing a result, so a later revision cannot silently replace the measured input. If NOAA has revised the prefix, replay requires a saved copy matching that digest. [Input manifest](../large-scale/row-inputs.json)

```sh
make -C research build/field-lanes.so
mkdir -p runs/row-study/sources runs/large/raw
curl -fL --range 0-10485759 https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_year/2020.csv.gz -o runs/row-study/sources/2020.csv.gz
python3 research/lattice-prediction/row_inputs.py gzip-prefix runs/row-study/sources/2020.csv.gz runs/large/raw/noaa-2020-prefix --sha256 d6421f0b2bbf8560f4ee580d643597950f249a555a00df6cbf59711cbff75690
python3 research/large-scale/entropy_bench.py lattice-rows-fields runs/large/raw/noaa-2020-prefix runs/row-study/fields.json
python3 research/large-scale/preprocess.py prepare lattice-rows-fields runs/large/raw/noaa-2020-prefix runs/row-study/fields.pre
python3 research/lattice-prediction/match_probe.py runs/row-study/fields.pre
```

For 1990, use the 1990 source URL, output name and hash in the same manifest. To regenerate the NCI control, first prepare the complete Silesia member with the [large-file input instructions](../large-scale/README.md#reproduce-a-result), then run the following in a directory where the output does not yet exist. It uses NumPy PCG64 with seed 301057 to order the non-LF bytes of each row fragment by a random key, breaking ties by original position.

```sh
python3 research/lattice-prediction/row_inputs.py shuffle runs/large/raw/nci runs/large/raw/nci-row-shuffled --sha256 8df3c7bbb83661ea7a145737ae4533cadb30f723e372bb1f0102a73ca1e6d55e
```

For the separate Covertype comparison, extract the original gzip member from UCI's published ZIP. The same prefix reader keeps the exact uncompressed bytes, including a partial final record. The manifest pins both archive layers and the measured input. [Blackard (1998), Covertype, CC BY 4.0](https://doi.org/10.24432/C50K5N)

```sh
curl -fL https://archive.ics.uci.edu/static/public/31/covertype.zip -o runs/row-study/sources/covertype.zip
unzip -p runs/row-study/sources/covertype.zip covtype.data.gz > runs/row-study/sources/covtype.data.gz
python3 research/lattice-prediction/row_inputs.py gzip-prefix runs/row-study/sources/covtype.data.gz runs/large/raw/covertype-prefix --sha256 bf1f664919a72ae6f44ea81268e7085b9b6d09ce3f6c8743207df8723f06ee98
python3 research/large-scale/entropy_bench.py lattice-rows-field-positions runs/large/raw/covertype-prefix runs/row-study/covertype.json
```
