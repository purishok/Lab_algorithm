#include "s5_sort.hpp"

#include <algorithm>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

template <typename Sorter>
void measure(std::size_t n, int repetition, const std::vector<Student>& source,
             const char* name, Sorter sorter, std::ostream& out) {
    auto rows = source; // Input duplication is excluded for both methods.
    auto begin = std::chrono::steady_clock::now();
    sorter(rows); // Includes all helper-structure construction.
    double milliseconds = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - begin).count();
    if (!std::is_sorted(rows.begin(), rows.end(), [](const Student& a, const Student& b) { return a.m_group < b.m_group; }))
        throw std::runtime_error(std::string(name) + " failed order check");
    out << n << ',' << repetition << ',' << name << ',' << milliseconds << '\n';
}

int main(int argc, char** argv) {
    try {
        if (argc != 5) {
            std::cerr << "Usage: benchmark_s5 students.csv results.csv standard.csv radix.csv\n";
            return 2;
        }
        auto all = read_students(argv[1]);
        if (all.size() != 100000) throw std::runtime_error("Expected 100000 students");
        std::ofstream out(argv[2]);
        if (!out) throw std::runtime_error("Cannot write results");
        out << "n,rep,method,sort_ms\n" << std::fixed << std::setprecision(6);
        const std::vector<std::size_t> sizes = {100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000};
        for (std::size_t n : sizes) {
            std::vector<Student> source(all.begin(), all.begin() + n);
            for (int rep = 1; rep <= 5; ++rep) {
                // Alternate method order to reduce systematic CPU-state bias.
                if (rep % 2) {
                    measure(n, rep, source, "standard", standard_group_sort, out);
                    measure(n, rep, source, "radix", radix_group_sort, out);
                } else {
                    measure(n, rep, source, "radix", radix_group_sort, out);
                    measure(n, rep, source, "standard", standard_group_sort, out);
                }
            }
            std::cerr << "S5 n=" << n << " complete\n";
        }
        auto standard = all, radix = all;
        standard_group_sort(standard);
        radix_group_sort(radix);
        write_students(argv[3], standard);
        write_students(argv[4], radix);
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
