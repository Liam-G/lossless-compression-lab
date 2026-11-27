# An atlas of the compression experiments

The project started with a question about an arithmetic expression on a whiteboard. It grew into two different practical problems. Can a large integer be regenerated more cheaply than sending its digits? Can a change of representation expose dependencies that a general compressor misses? The organized trials below preserve unsuccessful tests alongside successful ones. The [large-file measurements](../large-scale/README.md) identify which results have fresh, byte-verified archives.

## Where the evidence comes from

| Local source | What this repository preserves |
|---|---|
| `tesi_sperimentali_compressione.md` | Sixteen questions with working implementations and three cross-experiment studies. SHA-256 `48c7b5999966035bceb39e94f49bd6c464ee3d356734eb0814b41455289954e9`. [Experiment index](../../README.md) |
| `esperimenti_descrizioni_tecniche.txt` | All 23 method families, 149 report abstracts, 15 supplementary measurement files, 583 historical protocol directories, and the 51 dossier topics below. SHA-256 `e4c1709e1198e1ec38580c0e9918e310b826031e3e11d02a0853317cbbde745b`. [Reports](report-index.tsv) · [Additional measurements](supplementary.tsv) · [Protocol inventory](protocol-index.tsv) |
| Project-local conversation history | Research requests and design alternatives were matched to the register and implementations. Twenty nonempty local session records included continuations and overlapping conversations. The design questions appear below in English. |
| 2019 whiteboard image in `lab/whiteboard/lavagna-rapporto-repdigit.png` | The exact formula and the bounds on the integer and exponent are preserved below. Image SHA-256 `85d35a5bccdb66f7500eadce3ee6870ee2debf231818d8457649f330a50b934c`. |

The 583 directory entries identify where a script, protocol or measurement was recorded. Some historical intermediates were removed in a prior workspace cleanup. A report abstract describes the scope of its original evidence. A fresh benchmark row requires an actual archive that decodes every byte of the target.

## The whiteboard

For a base b ≥ 2, a digit 1 ≤ c < b and a repeat count r ≥ 1, the integer with r copies of digit c is G(b,c,r) = c(bʳ−1)/(b−1). The board proposed the larger alphabet d = G(b₁,c₁,r₁) / G(b₂,c₂,r₂), with both triples supplied or deterministically reconstructed. The division must be exact. Setting c₂ = r₂ = 1 gives denominator one in every admissible base. For d < 2²⁵⁶ in this last case, r₁ ≤ 256, attained by 256 binary ones. For genuine quotients a large numerator can cancel a large denominator, so that particular exponent bound no longer follows.

A testable extension puts the expression on either side of a concatenation below a product node. The decoder must know each child width, the factor, any sign or correction and whether it sees a reference or a new expression. The shared-factor experiment prices those fields together. [Whiteboard trees](../whiteboard-trees/README.md) · [Shared factor forest](../shared-factor-forest/README.md)

## The 51 topics from the discussion dossier

Numbers match the user-supplied appendix. Experiment numbers refer to the numbered folders. “Proposal” identifies a design for which the source does not establish a complete archive.

| § | Question or construction | Concrete experiment or evidence |
|---:|---|---|
| 1 | Interpret a whole file as an unsigned integer | Restore the original width, including leading zero bytes. Q and Neif are separate targets. Reports 007, 009 and 027. |
| 2 | Search for a locally favorable numeral base | Price the base, digit stream, escapes and transitions. Experiment 05 and the historical 256-base ZIP scan in report 080. |
| 3 | Encode repeated digits by base, digit and exponent | Experiment 01 compares a recipe with a literal block and with adaptive segmentation. |
| 4 | Plot representable numbers | The interactive heatmap counts attainable integers. The interval search separately charges positional information and the chosen recipe. |
| 5 | Divide two repdigits in different bases | Enumerate exact quotients and include both descriptions or the cost of an index. Reports 140–141. |
| 6 | Describe a near repdigit by a signed remainder | A search can find more candidates once errors are allowed. Report 119 compares gains with equal-length noise after charging corrections. |
| 7 | Connect the 2019 formula with the recorded systematic searches | The [restored native census](../whiteboard-census/README.md) reproduces the retained cost tables and prices 22,630,320 bytes of original witness records. The interval scanner and QFT1 decoder apply the same formula to other data. |
| 8 | Encode a number through its divisors | Factor nodes carry the remaining cofactor, exponent or factor ordinal and all required metadata. QRT and QPI1 give full-file examples. |
| 9 | Split a difficult factor into digit strings and recurse | Preserve widths and leading zeros at concatenation. QBF1 uses decimal groups, QRT uses bit fields, SFF1 adds reusable formula leaves. |
| 10 | Factor a nearby value and transmit a correction | Compare exact division with shifted targets. Experiment 02 and reports 022, 128 cover the arithmetic and cost model. |
| 11 | Reconstruct an integer through repeated multiply/add | Turn the path into affine instructions. Experiment 10 prices signed lanes and a dedicated frequent multiplier. |
| 12 | Generate that formula by dividing backwards | The Neif trace reconstructs the original file from one by reversing 219,001,648 recorded divisions. Report 023. |
| 13 | Choose among possible remainders | Test both a small signed correction and greater factor extraction. The recorded division policy creates its own statistical biases. Reports 023–025. |
| 14 | Serialize the arithmetic language | Use opcodes, literal escapes, ZigZag and varints. Measured affine-pair and source-listing inputs distinguish the binary grammar from printed formulas. |
| 15 | Give multiplier 240 a short code | The actual instruction capture contains 6,291,456 signed pairs. The historical compact bytes consumed to generate them are counted alongside the expanded benchmark. |
| 16 | Move big-integer calculations to C/GMP | Native QRT and quartic modules handle full Q. Measure computational cost separately from output size. |
| 17 | Compose affine operations as a balanced tree | Compose pairs as (a₂a₁, a₂b₁+b₂). The same instructions can then decode with a different operation schedule. Reports 023–025. |
| 18 | Generate enormous values from short fast-growing expressions | Powers, towers, repeated squaring and signed residuals were screened. A large magnitude alone leaves arbitrary low bits unspecified. |
| 19 | Test those formulas on the actual cofactor Q | Whole-file arithmetic descriptors are compared with canonical Q, the real-length matched controls and the V15 package. |
| 20 | Filter expensive expression synthesis modulo small integers | Rejection on a low-bit residue eliminates a candidate exactly. A survivor still requires a complete evaluation and exact residual. Register family 23. |
| 21 | Treat the bytes as a signal | Price exact coefficients and an inverse. The integer lifting project handles numerical data as discrete samples and rasters. |
| 22 | Use Walsh–Hadamard structure on bit planes | Experiment 09 sends a spectral model and XOR correction. The planted Boolean functions give a known control. |
| 23 | BWT on decimal digits | Preserve radix, original width and BWT primary index. The historical decimal screen is adjacent to the byte-scale BWT in experiment 13 and text views. |
| 24 | Measure generator coincidences by Monte Carlo | Reuse the complete search budget on random input. The three SHAKE generators enumerate 256³ seed triples per full search. |
| 25 | Rotate inputs to improve alignment | Circular offsets, byte order and target interval are part of the description. Experiment 12 tests rotation, patch and copy costs. |
| 26 | Optimize a symbol substitution or permutation | A permutation may increase agreement with a generator. The decoder needs its index or table. The Margolus experiment paid six bytes for the permutation. |
| 27 | Take a longest common subsequence or a copy from another file | Match length alone omits locations and edits. Experiment 12 and reports 048–058 account for the external reference. |
| 28 | Sort data and recover order with enumerative coding | Preserve the permutation rank, multiplicities and tie convention. Page-order experiments exploit genuinely known order. Reports 040–047. |
| 29 | Predict, take XOR or signed differences, and code what remains | Experiments 03 and 14 compare exact residual representations. Grid predictors add lag, mixed differences and bit planes. |
| 30 | Search for a cheap predecessor of a reversible automaton | Send the seed, rule, geometry, step and remaining data. GFH1, CBO1, TGF1 and F4D1 test different state spaces. |
| 31 | Apply an 8×8 binary automaton independently to words | CBO1 tests all times through 1,000 for individual matrices and compares a shared time per page. Reports 004–005. |
| 32 | Compare checkerboard, XOR, second-order and Margolus rules | Experiment 06 and the historical Wolfram-rule and block-permutation runs specify phases, boundaries and inverses. The [bitmap-tree experiment](../checkerboard-orbits/bitmap-trees.md) swaps the rule axes on identical source stamps and measures each inverse. |
| 33 | Investigate why a lower seed entropy can still lose | The seed and its time are dependent. Compare their joint serialized cost with raw storage on the original Neif target. |
| 34 | Observe the checkerboard interactively | The original workspace visualizer `gioca_automa.py` has an [English trajectory explorer](../checkerboard-orbits/explore.py). CBO1 makes the per-matrix and shared-clock hypotheses reproducible. |
| 35 | Extend reversible automata to larger alphabets | The [byte-valued checkerboard experiment](../modular-kronecker/README.md) adds and subtracts modulo 256 on two colors and tests the inverse on full archives. |
| 36 | Add spatial axes and a time axis | TGF1 runs six parity half-steps in three dimensions. F4D1 separately varies four axes and tests a noisy matrix model. |
| 37 | Approximate a large binary matrix by smaller factors | Recover X as UV XOR E. Store both factors and the error map, including literal and sparse alternatives. Experiment 08 and reports 028–031. |
| 38 | Introduce three factors, Kronecker products and tensor layouts | The [Kronecker implementation](../modular-kronecker/README.md) fits two 4 × 4 byte factors after reversing an orbit. Three unconstrained factors remain a separate proposal. |
| 39 | Place the reversible rule before or after factorization | Experiment 07 compares orderings. TGF1 tests rank after reversing 3D evolution and GFH1 recurses into factor data. |
| 40 | Choose equivalent factor bases by coded cost | For invertible S, (US)(S⁻¹V) gives the same product. Experiment 08 and F4D1 test swaps and basis additions, paying for transmitted factors. |
| 41 | Share repeated arithmetic subexpressions | Store one definition and price every later reference. Compare inline and shared encodings on exactly the same products. Experiment 11 and SFF1. |
| 42 | Add or otherwise compose distinct generators | QGS1 tests three seeds plus a signed difference. QFE1 uses products of consecutive integers and squares on successive residuals. |
| 43 | Distinguish symbol entropy from description length | A change of base or an entropy heatmap can change apparent entropy. An archive must price its alphabet, parameters, code stream and inverse. |
| 44 | Apply the counting argument to reversible evolution | A fixed bijection permutes states. Gains on a restricted family can arise when the selected inverse makes those states inexpensive under the chosen code. |
| 45 | Quantify the 12 MB random-file challenge | Saving 1% means saving 960,000 bits on a decimal 12 MB input. Count available short codewords and run the entire selector on matched uniform noise. |
| 46 | Search many mathematical representations per interval | Experiment 16 uses exact dynamic programming over offered intervals. The native carry tree allows a transform above or below a split. |
| 47 | Use minimum description length as the decision criterion | Price the complete alternatives, including the literal fallback. Several experiments explicitly show proxy statistics disagreeing with archive bytes. |
| 48 | Rank directions by evidence on structured and ordinary files | The large-file comparisons distinguish algebraic controls, real scientific bytes, structured model data, images, text and compressed executables. |
| 49 | Use a shared experiment platform | Sixteen numbered projects and the template expose reproducible variants. Native extensions document their original source and wire format. |
| 50 | Benchmark on several inputs with fair controls | Every row in the primary large suite requires at least 20 MiB and a full byte comparison. Transfer inputs, strong baselines and absolute archive bytes are recorded. |
| 51 | Search cheaply among equivalent arithmetic descriptions | The combined research tests division, correction, segmentation, recipe reuse, equivalent matrix factors and fast decoder inverses. Global optimality over unrestricted programs remains an open question. |

## The 23 families in the technical register

| Family | What was tried, and where to find it |
|---:|---|
| 01 | Whole-file accounting, decoding from scratch, conditional references, delivery of the decoder and replay. The original package, a cofactor, a model or a rate trace have different denominators. See the [measurement protocol](../../PROTOCOL.md). |
| 02 | Strides, nested rectangles, triangular or ragged rows, TLV columns, headers, shuffled controls and learning a predictor from shape. The historical triangle was a packed matrix of distances between 2,000 points. The [distance experiment](../distance-geometry/README.md) extends it to actual archives. The [ragged-row experiment](../lattice-prediction/ragged-rows.md) tests vertical prediction and field routing on weather, chemical records and prose. |
| 03 | Repdigits, exact cross-base quotients, adjacent products, power and zero nodes, prime ordinals and structured arithmetic examples. The 26-bit short-code census found 425 profitable values. The whiteboard, interval and prime-index projects cover different node grammars. |
| 04 | Statico M0/M1, grammar rule selection, word and capitalization transforms, and 381 backend/transform chains. The [text-view project](../text-views/README.md) prices an explicit front end followed by reversible sorting. |
| 05 | Irrational digits, integer sequences, sparseness in Walsh/Fourier space, generators, Langton's ant and Boolean functions, arbitrary layouts, copies and prior contexts. The original 1 KiB comparison grew from pure generators to generators plus copying and prediction. |
| 06 | Primary-index BWT and transformed patterns, multi-file archives, GPU coincidence scans, reset cadence and parallel scoring. On the 96,996,198-byte awarded FX2 archive, BWT with Zstd-19 was larger than plain Zstd-19. The supplementary files retain the exact run identities. |
| 07 | CM, CM2 and CM3 with adaptive contexts, match lengths, APM, second-layer mixing and LSTM size. The historical 256-cell full run was interrupted. The verified 192-cell result and the smaller fresh profiles have separate records. |
| 08 | Wikipedia page skeleton, revision and census fields, ranks, morphologies, redirects, article order, templates, URLs and causal title references. Report 130 reconstructs the entire billion-byte source from the FX2-conditioned stream and dictionary. |
| 09 | Define exactly which release the integer belongs to. FX2 has N = 3,072Q. Neif yielded a different exact factor of 37,632. The [reference experiment](../arithmetic-references/README.md) explicitly identifies each base. |
| 10 | Primality tests, bounded prime sieves and searching a correction around a large integer. Separate the cost of the remaining cofactor from the apparent simplicity of factors that were removed. |
| 11 | Scan bases 2–257 and mixed-arity quotient trees, minimize entropy, group digits, concatenate children and recurse. Report 080 gives the whole-number ZIP comparison. The QRT project repeats mixed and seeded splits. |
| 12 | Extract ELF structure, restore compiler/runtime components, model weights, order and dictionaries. Track portable single-file packages separately from external-reference and computational replay packages. |
| 13 | Exact division schedules, the affine multiplier/correction tape, grouped instructions, balanced evaluation and alternative encodings of the same trace. Reports 023–026 and experiment 10 include the instruction cost. |
| 14 | Factor binary grids into U, V and E, vary cell width and handle tails. Actual rank of the large Neif matrix was almost full. Fitting small factors moves the unexplained information to E. |
| 15 | Reverse checkerboard, second-order and Margolus systems. Search a predecessor, measure its entropy and jointly code its rule/phase/time. The 8×8, 3D and 4D projects keep different state geometries explicit. |
| 16 | Search 18 generator families for literal stretches, distance copies, recurrences and arithmetic constants. The historical selected intervals regenerated 187 bytes and saved 107 bytes after descriptors on Neif. Some constants were identified after looking at the prefix. |
| 17 | Restore headers and program segments from ELF geometry, compare independent whole-Neif packages and patch structural regions. A 632-byte prefix choice in EX2 yielded 89,346,212 bytes. Reports 009–014. |
| 18 | Search digit prefixes of signed sums of irrationals, backtrack over coefficients and place checkpoints between literal and generated segments. The historical interactive investigation and experiment 04 charge every restart. |
| 19 | Learn one 2×2 Margolus permutation shared across J16 boundary words. Across 144 tested combinations the best resulting 6,955-byte stream lost to the previous 6,635-byte KT2 stream. |
| 20 | Define a grammar rule inline on first use, then refer to its frequency class and index. Statico M1 built 553,204 rules over 94 passes on enwik8. The [native grammar](../statico/README.md) includes its decoder. |
| 21 | Split decimal groups, remove factors through a primorial GCD and store the remaining cofactor. QBF1 preserves decimal widths and the final newline. Compare its archive with canonical binary Q as well as with its much larger decimal source file. |
| 22 | Sum three independent SHAKE256 integers and store the signed residual. The sorted pair-sum search covers all 16,777,216 triples. The [generator project](../generator-sums/README.md) includes planted, noise and full-Q trials. |
| 23 | Greedily sum squares or consecutive products, find roots modulo powers of two, and split a sparse prefix from a square suffix. A low-64-bit screen rejected the enumerated short-seed expressions. The [integer formulas](../integer-formulas/README.md) regenerate complete descriptors. |

## Questions preserved from the local conversations

- **Where should a factor tree branch?** Compare the divisions at a node, an initial split and a split below the multiplier. An exact product can reveal a quotient formula across a byte boundary. A downstream entropy coder can also exploit ordinary structure after an arithmetic change of representation.
- **Can repeated mathematical work become a dictionary?** Compare direct coding, an inline recipe and a recipe referenced several times. Store the width, signed adjustment, operands, table and index stream. A more general graph search with unrestricted operations remains a proposal.
- **Does an expensive encoder buy a fast decoder?** The encoder may inspect many rule/step pairs, divisors, bases and program nodes. The decoder follows one explicitly stored path. Timing both passes exposes cases where the delivered formula has little value for the time spent.
- **Can the rule, clock or residual be shared?** Evaluate individual seed clocks against a page-wide clock, process the three axes separately, or add a temporal axis. Try interchangeable GF(2) bases and count the complete residual. A recorded 1,000-step search is available in the checkerboard project.
- **What if a header, tensor or file has a different geometry?** The source proposed triangular and ragged layouts, irregular alphabets, bit layers, transposed words, tabular columns, 2D image regions, 3D planes and trajectories. The structure-specific tests include both documents and image/video samples.
- **Can long-prefix matches survive actual serialization?** A generator may match many bits after a search over rules, order, rotation and seed. An independent noise control and an archive carrying the winning choice test whether that search paid for itself.
- **Can signed irrational sums be restarted at just the right locations?** Literal fallback, coefficient bounds, number of terms, the checkpoint position and exact digit generation all matter. Experiment 04 retains these costs.
- **What does a one-gigabyte claim measure?** Distinguish the raw corpus, its prepared tape, the compressed stream, the executable, the decoder package and a reference a receiver might already own. The large run includes complete enwik9 measurements and links back to the original numerical and probabilistic studies.
