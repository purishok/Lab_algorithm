#include "v4_alternatives.hpp"

#include <algorithm>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>

struct Operation { unsigned char kind; std::size_t student; std::size_t group; };

template <typename Database>
void measure(const char* name, const std::vector<Student>& students,
             const std::vector<std::string>& groups, const std::vector<Operation>& tape,
             std::ostream& out, double seconds) {
    Database db(students);
    using Clock = std::chrono::steady_clock;
    std::uint64_t counts[3]{};
    std::uint64_t checksum = 0;
    std::size_t pos = 0;
    auto start = Clock::now();
    auto deadline = start + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
    for (;;) {
        for (int j = 0; j < 64; ++j) {
            const auto& op = tape[pos];
            if (++pos == tape.size()) pos = 0;
            ++counts[op.kind - 1];
            if (op.kind == 1) checksum += db.largest_groups().size();
            else if (op.kind == 2) checksum += db.change_group(db.students()[op.student].m_email, groups[op.group]);
            else checksum += db.highest_average_groups().size();
        }
        if (Clock::now() >= deadline) break;
    }
    const double elapsed = std::chrono::duration<double>(Clock::now() - start).count();
    if (!db.validate()) throw std::runtime_error(std::string(name) + " failed validation");
    out << name << ',' << elapsed << ',' << counts[0] + counts[1] + counts[2];
    for (auto count : counts) out << ',' << count;
    out << ',' << checksum << '\n';
    std::cerr << name << ": " << counts[0] + counts[1] + counts[2] << " operations in " << elapsed << " seconds\n";
}

int main(int argc, char** argv) {
    try {
        if (argc != 4) {
            std::cerr << "Usage: compare_v4 students.csv comparison.csv seconds\n";
            return 2;
        }
        const double seconds = std::stod(argv[3]);
        if (seconds <= 0) throw std::invalid_argument("seconds must be positive");
        auto students = read_students(argv[1]);
        if (students.size() != 100000) throw std::runtime_error("Expected 100000 students");
        V4Index initial(students);
        auto groups = initial.groups();
        std::sort(groups.begin(), groups.end());
        std::mt19937 rng(20261016);
        std::uniform_int_distribution<std::size_t> student_dist(0, students.size() - 1);
        std::uniform_int_distribution<std::size_t> group_dist(0, groups.size() - 1);
        std::vector<Operation> tape;
        tape.reserve(25000);
        for (int block = 0; block < 100; ++block) {
            std::vector<Operation> batch;
            for (int kind = 1; kind <= 3; ++kind) {
                const int count = kind == 1 ? 50 : 100;
                for (int i = 0; i < count; ++i)
                    batch.push_back(Operation{static_cast<unsigned char>(kind), student_dist(rng), group_dist(rng)});
            }
            std::shuffle(batch.begin(), batch.end(), rng);
            tape.insert(tape.end(), batch.begin(), batch.end());
        }
        std::ofstream out(argv[2]);
        if (!out) throw std::runtime_error("Cannot open comparison file");
        out << "approach,elapsed_s,operations,op1_count,op2_count,op3_count,checksum\n";
        out << std::fixed << std::setprecision(6);
        measure<V4Vector>("vector_scan", students, groups, tape, out, seconds);
        measure<V4AggregateMap>("aggregate_map", students, groups, tape, out, seconds);
        measure<V4Index>("ranked_sets", students, groups, tape, out, seconds);
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
