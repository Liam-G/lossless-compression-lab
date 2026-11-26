CXX ?= g++
CXXFLAGS ?= -O2 -std=c++20 -march=native -Wall -Wextra -g
CFLAGS_SAIS = -O2 -march=native -w
HDRS = $(wildcard src/*.hpp)

UT_OBJS = $(if $(wildcard src/grammar.cpp),work/grammar.o work/libsais.o,)

all: statico unstatico unit_tests

work/libsais.o: third_party/libsais/libsais.c third_party/libsais/libsais.h
	@mkdir -p work
	$(CC) $(CFLAGS_SAIS) -c $< -o $@

work/grammar.o: src/grammar.cpp $(HDRS)
	@mkdir -p work
	$(CXX) $(CXXFLAGS) -c $< -o $@

statico: src/statico.cpp $(HDRS) $(UT_OBJS)
	$(CXX) $(CXXFLAGS) src/statico.cpp $(UT_OBJS) -o $@

unstatico: src/unstatico.cpp $(HDRS)
	$(CXX) $(CXXFLAGS) src/unstatico.cpp -o $@

unit_tests: tests/unit_tests.cpp $(HDRS) $(UT_OBJS)
	$(CXX) $(CXXFLAGS) tests/unit_tests.cpp $(UT_OBJS) -o $@

unit_tests_asan: tests/unit_tests.cpp $(HDRS) src/grammar.cpp
	$(CXX) -O1 -g -std=c++20 -fsanitize=address,undefined tests/unit_tests.cpp src/grammar.cpp third_party/libsais/libsais.c -o $@

asan: unit_tests_asan
	./unit_tests_asan

test: all
	./unit_tests
	python3 -I tests/edge_cases.py . work/edge

clean:
	rm -f statico unstatico unit_tests unit_tests_asan work/*.o

.PHONY: all test asan clean
