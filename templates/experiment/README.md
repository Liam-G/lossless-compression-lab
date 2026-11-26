# Experiment NN · Descriptive title

## Question and prior work

State the falsifiable question and what counts as a win. Identify the starting prototype, its input and its measured result. Label historical figures separately from results generated here.

### Source files and compatibility

List exact workspace-relative paths and the role of each source. Distinguish encoder and decoder implementations, benchmark drivers, data generators and historical measurements. For an existing format, include a compatibility vector or describe how the inverse was verified.

## Run the experiment

Give requirements, working directory and copyable commands for encoding, decoding, verifying exact output, running tests and reproducing the benchmark. Link to the project implementation, its regression tests and its entry in the shared benchmark runner. Use relative paths and document any external corpus.

## Variants and format

Define the control, each component alone and their combination, or specify the relevant alternatives for a multiway comparison. Hold the final coder fixed when comparing transforms. Describe every transmitted field, the inverse, the decoder version and any reference or model the receiver needs.

## Inputs and measurement

Use at least 20 MiB raw input per primary benchmark and verify an independent decode. Use small inputs for diagnostic tests. Specify the planted structure, equal-length random control and relevant real file family. Give seeds, hashes, parameter selection and held-out evaluation procedure. Describe the timed regions, memory units, repetitions and verification method. Report free-reference and delivered-reference costs separately where applicable.

## Results

Link to the project section in research/large-scale/results/by-experiment.md and summarize the most informative results here. The canonical machine-readable records live in research/large-scale/results/archives.jsonl. Keep any original small diagnostic tables under results/reference. Report archive bytes, metadata bytes, search and decode time, peak memory, round-trip equality and decoder delivery cost. Compare with raw input and Zstd. For a two-component experiment, calculate min(bytes A, bytes B) − bytes A+B. Give the crossover or other experiment-specific outcome and explain the limits of the evidence.

## Large-file benchmark

Give one reproducible primary result, the exact raw and archive bytes, the delivered total for a conditional archive and the same-input Zstandard result. Link to the dataset and project sections in the shared results.

## Connections

Name the experiments that consume or supply data, the format they exchange and the comparison that exchange enables.
