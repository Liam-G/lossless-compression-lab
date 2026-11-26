CXX ?= c++
CXXFLAGS ?= -O3 -std=c++17
BUILD := build

all: $(BUILD)/orbit.so $(BUILD)/factor-tree $(BUILD)/quartic $(BUILD)/evolve.so $(BUILD)/shape $(BUILD)/cm3 $(BUILD)/interval-scan $(BUILD)/product-scan

$(BUILD):
	mkdir -p $@

$(BUILD)/factor-tree: factor-trees/factor_tree.cpp statico/src/rc.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) $< -lgmpxx -lgmp -o $@

$(BUILD)/quartic: quartic-trees/quartic.cpp | $(BUILD)
	$(CXX) $(CXXFLAGS) $< -lgmpxx -lgmp -o $@

$(BUILD)/evolve.so: tensor-orbits/evolve.cpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -shared -fPIC $< -o $@

.PHONY: all

$(BUILD)/shape: shape-context/shape.cpp statico/src/rc.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) $< -o $@

$(BUILD)/orbit.so: hierarchical-gf2/orbit.cpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -shared -fPIC $< -o $@


$(BUILD)/cm3: context-mixer/cm3.cpp $(wildcard context-mixer/*.hpp) statico/src/io.hpp statico/src/sha256.hpp | $(BUILD)
	$(CXX) -O3 -std=c++20 -march=native -ffast-math $< -o $@

$(BUILD)/interval-scan: repdigit-intervals/scan.cpp | $(BUILD)
	$(CXX) $(CXXFLAGS) $< -o $@

$(BUILD)/product-scan: repdigit-intervals/product_scan.cpp | $(BUILD)
	$(CXX) $(CXXFLAGS) $< -o $@
