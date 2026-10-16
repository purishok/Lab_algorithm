#include "v4_index.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>

struct Operation { unsigned char kind; std::size_t student; std::size_t group; };

int main(int argc, char** argv) {
    try {
        if (argc != 5) {
            std::cerr << "Usage: benchmark students.csv results.csv seconds repetitions\n";
            return 2;
        }
        const double seconds = std::stod(argv[3]);
        const int repetitions = std::stoi(argv[4]);
        if (seconds <= 0 || repetitions <= 0) throw std::invalid_argument("seconds and repetitions must be positive");
        auto all = read_students(argv[1]);
        if (all.size() < 100000) throw std::runtime_error("Expected at least 100000 students");
        const std::vector<std::size_t> sizes = {100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000};
        std::ofstream out(argv[2]);
        if (!out) throw std::runtime_error("Cannot open results file");
        out << "n,rep,operations,op1_count,op2_count,op3_count,op1_mean_ns,op2_mean_ns,op3_mean_ns,estimated_bytes,elapsed_s,checksum\n";
        out << std::fixed << std::setprecision(3);
        using Clock = std::chrono::steady_clock;
        for (auto n : sizes) {
            std::vector<Student> initial(all.begin(), all.begin() + n);
            for (int rep = 0; rep < repetitions; ++rep) {
                V4Index db(initial);
                auto group_names = db.groups();
                std::mt19937 rng(static_cast<unsigned>(20261016 + n * 31 + rep));
                std::uniform_int_distribution<std::size_t> student_dist(0, n - 1);
                std::uniform_int_distribution<std::size_t> group_dist(0, group_names.size() - 1);
                std::vector<Operation> work;
                work.reserve(25000);
                // Exactly 50:100:100 within a shuffled, reusable 25000-operation tape.
                for (int kind = 1; kind <= 3; ++kind) {
                    const int count = kind == 1 ? 5000 : 10000;
                    for (int j = 0; j < count; ++j) work.push_back(Operation{static_cast<unsigned char>(kind), student_dist(rng), group_dist(rng)});
                }
                std::shuffle(work.begin(), work.end(), rng);
                const auto memory = db.estimated_bytes();
                std::uint64_t counts[3]{};
                std::uint64_t samples[3]{};
                std::uint64_t nanoseconds[3]{};
                std::uint64_t checksum = 0;
                std::size_t pos = 0;
                auto begin = Clock::now();
                auto deadline = begin + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
                for (;;) {
                    for (int block = 0; block < 1024; ++block) {
                        const auto& op = work[pos];
                        ++pos;
                        if (pos == work.size()) pos = 0;
                        const unsigned k = op.kind - 1;
                        // Sampling limits timer overhead in the throughput measurement.
                        const bool sample = (counts[k] & 127U) == 0;
                        Clock::time_point t0;
                        if (sample) t0 = Clock::now();
                        if (op.kind == 1) checksum += db.largest_groups().size();
                        else if (op.kind == 2) checksum += db.change_group(db.students()[op.student].m_email, group_names[op.group]);
                        else checksum += db.highest_average_groups().size();
                        if (sample) {
                            nanoseconds[k] += std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - t0).count();
                            ++samples[k];
                        }
                        ++counts[k];
                    }
                    if (Clock::now() >= deadline) break;
                }
                const auto elapsed = std::chrono::duration<double>(Clock::now() - begin).count();
                if (!db.validate()) throw std::runtime_error("Index inconsistency after benchmark");
                out << n << ',' << rep + 1 << ',' << counts[0] + counts[1] + counts[2];
                for (auto c : counts) out << ',' << c;
                for (int k = 0; k < 3; ++k) out << ',' << static_cast<double>(nanoseconds[k]) / samples[k];
                out << ',' << memory << ',' << elapsed << ',' << checksum << '\n';
                out.flush();
                std::cerr << "n=" << n << " rep=" << rep + 1 << " operations=" << counts[0] + counts[1] + counts[2] << '\n';
            }
        }
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
