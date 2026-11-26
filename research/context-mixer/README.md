# CM3 context mixing

## Question and prior work

How much does the lab's text compressor gain when it combines byte and word contexts, longer matches, a second mixer and a recurrent predictor? The CPU implementation and predictor headers are from `lab/arena`. The historic full-file run used the v9 configuration and the binary called cm3_v11. The workspace source has later optional predictors. The retained log records the original result.

## Run the experiment

```sh
mkdir -p runs
python3 research/context-mixer/benchmark.py "$CORPUS/enwik8/enwik8" runs/cm3-prefix.csv
CM3_BITS=13 research/build/cm3 c research/statico/tests/data/sample.txt runs/sample.cm
CM3_BITS=13 research/build/cm3 d runs/sample.cm runs/sample.decoded
cmp research/statico/tests/data/sample.txt runs/sample.decoded
```

The benchmark clears inherited CM3 settings and supplies the same explicit profile for encoding and decoding. For the historical configuration, run the following in a clean shell from the repository root. This substantial run originally took about 6,200 seconds to encode and 6,300 seconds to decode, with 2.8 GB of context tables.

```sh
(
  set -a
  . ./research/context-mixer/cm3_v9.config
  set +a
  research/build/cm3 c "$CORPUS/enwik8/enwik8" runs/enwik8.cm
  research/build/cm3 d runs/enwik8.cm runs/enwik8.restored
  cmp "$CORPUS/enwik8/enwik8" runs/enwik8.restored
)
```

## Variants and format

Each predictor supplies a probability for the next bit. The mixer combines them before arithmetic coding. Both processors update from the same decoded prefix. The profile and floating-point implementation are part of the shared decoder configuration. Use the same binary and CPU for encoding and decoding. The file carries its length and range-coded data. The benchmark directly compares restored contents and hashes the source.

## Inputs, results and interpretation

On the first 131,072 bytes of enwik8, small context tables produced a 34,010-byte archive. The match and second-layer profile produced 33,759. Adding a 32-cell LSTM reduced that to 33,727. The original full 100,000,000-byte run used larger context tables and a 192-cell LSTM. Its verified archive measured 17,811,463 bytes. The prefix run was repeated here. The full result comes from the retained encode/decode log. [Fresh benchmark](results/enwik8-prefix.csv) · [Historical full-file log](results/original-enwik8.log)
