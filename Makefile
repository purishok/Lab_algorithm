CXX ?= clang++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -Wpedantic

build/test_v4: src/v4_index.cpp src/v4_index.hpp tests/test_v4.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc src/v4_index.cpp tests/test_v4.cpp -o $@

build/benchmark: src/v4_index.cpp src/v4_index.hpp src/benchmark.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc src/v4_index.cpp src/benchmark.cpp -o $@

test: build/test_v4
	./build/test_v4 students.csv

benchmark: build/benchmark
	./build/benchmark students.csv results/v4_benchmark.csv 10 5

.PHONY: test benchmark
