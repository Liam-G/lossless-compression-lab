# Rerun of every published benchmark receipt

For this report every receipt in [`archives.jsonl`](../../research/large-scale/results/archives.jsonl) was run again from scratch with [`rerun_all.py`](../../research/large-scale/rerun_all.py): encode, decode in a separate process, compare every byte, then compare the new archive with the published one.

| Outcome | Receipts |
|---|---:|
| Identical archive (same size and SHA-256) | 535 |
| Same size, different bytes | 0 |
| Different size | 0 |
| Failed (encoder, decoder or comparison) | 0 |
| Not rerun (enwik9 inputs; this report tests on enwik8) | 5 |
| Still running when this page was generated | 234 |
