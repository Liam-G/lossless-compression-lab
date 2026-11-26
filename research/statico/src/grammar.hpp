// Grammar: main sequence + production rules. Symbol < 256 is a byte; symbol 256+i is rules[i].
// Rules form a DAG (no cycles); a body may reference any other rule.
#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>

struct Grammar {
    std::vector<uint32_t> main;
    std::vector<std::vector<uint32_t>> rules;
};

struct GrammarParams {
    double production_cost = 6.0;   // bits charged per new rule on top of its definition
    double batch_frac = 0.05;       // fraction of profitable candidates tried per round
    size_t min_batch = 64;
    int verbose = 0;
};

std::vector<uint8_t> expand(const Grammar& g);   // iterative, no recursion
Grammar build_grammar(const uint8_t* data, size_t n, const GrammarParams& p);
