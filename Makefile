CXX ?= clang++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -Wpedantic

build/test_v4: src/v4_index.cpp src/v4_index.hpp tests/test_v4.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc src/v4_index.cpp tests/test_v4.cpp -o $@

build/benchmark: src/v4_index.cpp src/v4_index.hpp src/benchmark.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc src/v4_index.cpp src/benchmark.cpp -o $@

build/test_v4_alternatives: src/v4_index.cpp src/v4_alternatives.cpp src/v4_alternatives.hpp tests/test_v4_alternatives.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc src/v4_index.cpp src/v4_alternatives.cpp tests/test_v4_alternatives.cpp -o $@

build/compare_v4: src/v4_index.cpp src/v4_alternatives.cpp src/v4_alternatives.hpp src/compare_v4.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc src/v4_index.cpp src/v4_alternatives.cpp src/compare_v4.cpp -o $@

build/test_s5: src/v4_index.cpp src/s5_sort.cpp src/s5_sort.hpp tests/test_s5.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc src/v4_index.cpp src/s5_sort.cpp tests/test_s5.cpp -o $@

build/benchmark_s5: src/v4_index.cpp src/s5_sort.cpp src/s5_sort.hpp src/benchmark_s5.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc src/v4_index.cpp src/s5_sort.cpp src/benchmark_s5.cpp -o $@

build/demo_v4: src/v4_index.cpp src/v4_index.hpp src/demo_v4.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc src/v4_index.cpp src/demo_v4.cpp -o $@

test: build/test_v4 build/test_v4_alternatives build/test_s5
	./build/test_v4 students.csv
	./build/test_v4_alternatives students.csv
	./build/test_s5 students.csv build/test_s5_output.csv

benchmark: build/benchmark
	./build/benchmark students.csv results/v4_benchmark.csv 10 5

compare: build/compare_v4
	./build/compare_v4 students.csv results/v4_comparison.csv 10

sort-benchmark: build/benchmark_s5
	./build/benchmark_s5 students.csv results/s5_benchmark.csv results/s5_standard.csv results/s5_radix.csv

verify-results:
	python3 tests/verify_outputs.py

.PHONY: test benchmark compare sort-benchmark verify-results
