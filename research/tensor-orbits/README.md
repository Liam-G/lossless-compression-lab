# Reversible 3D automata before GF(2) panel coding

## Question and prior work

A 3D automaton can spread local low-rank structure across planes. Can a decoder recover the original volume cheaply if the encoder stores an earlier state? The native kernel comes from `lab/hutter/divisors/q-correzioni-fattori/encoder-cofattori/cmix-neif-2.0/griglie-intere/automi/inverso/passi.cpp`. Historically it was applied to U, V and an XOR correction E derived from a Neif archive. Here it is paired with an exact panel coder on ordinary file bytes.

## Run the experiment

```sh
mkdir -p runs
python3 research/tensor-orbits/codec.py encode "$CORPUS/canterbury/ptt5" runs/fax.tgf --profile combined
python3 research/tensor-orbits/codec.py decode runs/fax.tgf runs/fax.bin
cmp "$CORPUS/canterbury/ptt5" runs/fax.bin
python3 research/tensor-orbits/benchmark.py "$CORPUS" runs/volumes
```

## Variants and format

Each full 8 KiB slab is a volume of 64 planes, each 16 rows by 64 bits. A step updates alternating parities along x, y and z in six half-steps with zero boundaries. A cell XORs either its preceding neighbor or the AND of its two neighbors along the axis. An individual half-step is its own inverse because its donors remain fixed. Applying the six half-steps in reverse order therefore gives a predecessor.

For each candidate state, the panel coder groups a plane into eight 16 × 8 binary matrices. Rank zero needs only a tag. Rank one or two carries basis rows and binary coordinates. Higher rank escapes to literal row bytes. Tags, bases, coordinates and literal panels form separate lanes. Direct, orbit-only, rank-only and combined profiles all use DEFLATE level 6 on the candidate payload. The four-byte slab record pays for method, rule, step and compressed length. All four share a 12-byte file header. A partial slab can enter the geometry search if it contains whole planes.

## Inputs, results and interpretation

| Input | Direct | Orbit only | Rank only | Both | XZ extreme |
|---|---:|---:|---:|---:|---:|
| Evolved rank-two volume, 256 KiB | 259,175 | 216,650 | 259,157 | 100,339 | 258,752 |
| Full Canterbury fax | 56,191 | 56,186 | 56,032 | 56,027 | 39,860 |
| Silesia MR, first MiB | 377,578 | 377,578 | 299,013 | 298,966 | 264,592 |
| Silesia X-ray, first MiB | 788,099 | 787,711 | 627,116 | 627,116 | 536,956 |

The plant uses independent rank-two panel bases and then evolves each slab forward by a search-supported distance. The combined decoder recovers this construction. On MR almost all the gain came from the panel representation, with 47 additional bytes from the orbit search. The same extra step saved five bytes on the fax and zero on X-ray, uniform noise, the spreadsheet and the enwik8 prefix. [All comparisons](results/comparisons.csv) · [Rule and step selections](results/trials.csv)
