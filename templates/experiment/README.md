# Experiment NN · Descriptive title

## Question and prior work

State the falsifiable question and what counts as a win. Identify the starting prototype, its input and its measured result. Label historical figures separately from results generated here.

### Source files and compatibility

List exact workspace-relative paths and the role of each source. Distinguish encoder and decoder implementations, benchmark drivers, data generators and historical measurements. For an existing format, include a compatibility vector or describe how the inverse was verified.

## Run the experiment

Give requirements, working directory and copyable commands for encoding, decoding, verifying exact output, running tests and reproducing the benchmark. Each experiment folder owns its implementation, tests, benchmark driver and reference results. Use relative paths and document any external corpus.

## Variants and format

Define the control, each component alone and their combination, or specify the relevant alternatives for a multiway comparison. Hold the final coder fixed when comparing transforms. Describe every transmitted field, the inverse, the decoder version and any reference or model the receiver needs.

## Inputs and measurement

Specify the planted structure, equal-length random control and relevant real file family. Give seeds, hashes, parameter selection and held-out evaluation procedure. Describe the timed regions, memory units, repetitions and verification method. Report free-reference and delivered-reference costs separately where applicable.

## Results

Include raw per-file measurements under results/reference and summarize them here. Report archive bytes, metadata bytes, search and decode time, peak memory, round-trip equality and decoder delivery cost. Compare with raw input and Zstd. For a two-component experiment, calculate min(bytes A, bytes B) − bytes A+B. Give the crossover or other experiment-specific outcome and explain the limits of the evidence.

## Connections

Name the experiments that consume or supply data, the format they exchange and the comparison that exchange enables.
