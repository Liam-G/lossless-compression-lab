# Wikipedia page order, algebraic templates and primed context mixing

## Question and prior work

Does grouping structurally similar pages make their prose or mathematical slots cheaper to reproduce? Three original implementations survive in `lab/hutter/shapes9/wiki_order.py`, `wiki_templates.py` and `wiki_archive.py`. The last uses the multi-member CM3 container from `lab/arena/cm3_parallel.py`. This folder includes the transforms, original WCM1 and C3P1 containers and a separate selector that prices the representations with Zstandard or XZ.

## Run the experiment

```sh
python3 research/wiki-structures/codec.py encode runs/large/raw/wiki-transfer runs/wiki.wks --profile joint
python3 research/wiki-structures/codec.py decode runs/wiki.wks runs/wiki.restored
cmp runs/large/raw/wiki-transfer runs/wiki.restored
python3 research/large-scale/bench.py runs/large/raw/wiki-transfer runs/primed.jsonl wcm-literal wcm-literal-primed wcm-similar-template-primed
```

## Variants and format

- Reorder complete pages by title or by deterministic similarity of title and article terms. Original increasing page IDs restore their order without transmitting a permutation. Partial pages and the outer envelope retain their positions.
- Parse repeated line templates with integer, percentage and link slots. Encode the slot literally, predict it from earlier values, or use a sum, difference or percentage of other known columns. The template dictionary, column parameters, escapes and line schedule travel in the stream.
- Replace a wiki link target by an index into recoverable article titles or a transmitted vocabulary. The decoder receives exact byte gaps and finds the same title list in the remaining text. This additional view pays the cost of each gap and symbol.
- WKS1 prices these alternatives in 8 MiB banks with Zstandard 6. Its XZ profile reprices the strongest two quick candidates and the original bank. WCM1 instead applies a single specified transform and embeds C3P1, which hashes its binary and configuration. Priming encodes one 65,536-byte prefix and lets the other four CM3 members learn from it.

## Inputs and measurement

Two disjoint 24 MiB enwik8 slices are fixed in the input manifest. The second slice starts at byte 67,108,864 and contains partial pages at the boundaries. Every measured profile includes a separate decoder process and a complete byte comparison. See the [source and archive hashes](../large-scale/results/archives.jsonl).

## Results

At Zstandard 6 the joint selector used 8,223,663 bytes on the first slice versus 8,267,789 for the matched direct representation. On the second slice it used 8,223,878 versus 8,283,833. Ordering alone used 8,229,885 on that second slice. The standalone link view selected the unmodified representation in every bank of both slices. Whole-file XZ extreme and the tested CM3 models produce smaller text archives. [All profiles by input](../large-scale/results/by-dataset.md#wiki-transfer)

On the disjoint 25,165,824-byte Wikipedia transfer window, four independently decodable CM3 members used 5,345,330 bytes in total. Encoding the first 65,536 source bytes as a primer, then using those decoded bytes to initialize the body members, reduced the complete archive to 5,331,459 bytes. [Measured sizes and profiles](../large-scale/results/by-dataset.md#wiki-transfer)

## Large-file benchmark

The [primary measurements for this experiment](../large-scale/results/by-experiment.md#wiki-structures) list complete archives on raw inputs of at least 20 MiB. Each entry links to the same-input baselines and records the cost of any required reference.

## Connections

[Text fields and context sorting](../text-views/README.md) · [CM3 predictors](../context-mixer/README.md) · [Historical template and ordering reports](../evidence/supplementary.tsv)
