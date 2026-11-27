CXX ?= c++
CXXFLAGS ?= -O3 -std=c++17
BUILD := build

all: $(BUILD)/orbit.so $(BUILD)/factor-tree $(BUILD)/quartic $(BUILD)/evolve.so $(BUILD)/shape $(BUILD)/cm3 $(BUILD)/interval-scan $(BUILD)/product-scan \
	$(BUILD)/prime-indices \
	$(BUILD)/checker-orbit.so \
	$(BUILD)/text-views.so \
	$(BUILD)/decimal-blocks \
	$(BUILD)/panel-factors.so \
	$(BUILD)/motion.so $(BUILD)/cellular-rules.so $(BUILD)/whiteboard-census $(BUILD)/whiteboard-census-host $(BUILD)/field-lanes.so

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


$(BUILD)/prime-indices: prime-index-trees/prime_indices.cpp statico/src/rc.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) $< -o $@


$(BUILD)/checker-orbit.so: checkerboard-orbits/orbit.cpp | $(BUILD)
	$(CXX) -O3 -std=c++20 -march=native -shared -fPIC $< -o $@


$(BUILD)/sais.o: statico/third_party/libsais/libsais.c statico/third_party/libsais/libsais.h | $(BUILD)
	$(CC) -O3 -fPIC -c $< -o $@

$(BUILD)/text-views.so: text-views/move.cpp $(BUILD)/sais.o | $(BUILD)
	$(CXX) $(CXXFLAGS) -shared -fPIC $^ -o $@


$(BUILD)/decimal-blocks: factor-trees/decimal_blocks.cpp | $(BUILD)
	$(CXX) $(CXXFLAGS) $< -lgmpxx -lgmp -o $@


$(BUILD)/panel-factors.so: four-dimensional-factors/panels.cpp | $(BUILD)
	$(CXX) -O3 -std=c++20 -march=native -shared -fPIC $< -o $@


$(BUILD)/motion.so: motion-residuals/motion.cpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -shared -fPIC $< -o $@

$(BUILD)/cellular-rules.so: learned-cellular-rules/rules.cpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -shared -fPIC $< -o $@

$(BUILD)/whiteboard-census: whiteboard-census/enumerate.c | $(BUILD)
	$(CC) -O3 -std=gnu11 $< -lgmp -lm -o $@

$(BUILD)/whiteboard-census-host: whiteboard-census/enumerate.c | $(BUILD)
	$(CC) -O3 -march=native -std=gnu11 $< -lgmp -lm -o $@

$(BUILD)/field-lanes.so: lattice-prediction/field_lanes.cpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -shared -fPIC $< -o $@
