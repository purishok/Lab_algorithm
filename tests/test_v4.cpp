#include "v4_index.hpp"

#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
#include <random>
#include <stdexcept>

static Student student(std::string email, std::string group, int cents) {
    Student s;
    s.m_email = std::move(email);
    s.m_group = std::move(group);
    s.rating_cents = cents;
    s.m_rating = cents / 100.0f;
    return s;
}

static std::vector<std::string> reference(const std::vector<Student>& rows, bool average) {
    std::map<std::string, std::pair<std::int64_t, std::size_t>> groups;
    for (const auto& s : rows) {
        auto& a = groups[s.m_group];
        a.first += s.rating_cents;
        ++a.second;
    }
    std::vector<std::string> result;
    for (const auto& [group, a] : groups) {
        if (result.empty()) { result.push_back(group); continue; }
        const auto& b = groups.at(result.front());
        const std::int64_t lhs = average ? a.first * b.second : static_cast<std::int64_t>(a.second);
        const std::int64_t rhs = average ? b.first * a.second : static_cast<std::int64_t>(b.second);
        if (lhs > rhs) result = {group};
        else if (lhs == rhs) result.push_back(group);
    }
    return result;
}

int main(int argc, char** argv) {
    assert(argc == 2);
    V4Index empty({});
    assert(empty.largest_groups().empty());
    assert(empty.highest_average_groups().empty());
    assert(!empty.change_group("missing", "Z"));
    assert(empty.validate());

    std::vector<Student> rows = {student("a", "A", 100), student("b", "B", 200), student("c", "B", 0), student("d", "A", 100)};
    V4Index db(rows);
    assert((db.largest_groups() == std::vector<std::string>{"A", "B"}));
    assert((db.highest_average_groups() == std::vector<std::string>{"A", "B"}));
    assert(!db.change_group("none", "A"));
    assert(db.change_group("a", "A"));
    assert(db.change_group("b", "A"));
    rows[1].m_group = "A";
    assert(db.validate());
    assert(db.largest_groups() == reference(rows, false));
    assert(db.highest_average_groups() == reference(rows, true));
    assert(db.change_group("c", "C"));
    rows[2].m_group = "C";
    assert(db.validate());
    assert(db.largest_groups() == reference(rows, false));
    assert(db.highest_average_groups() == reference(rows, true));

    std::mt19937 rng(19);
    for (int i = 0; i < 100; ++i) rows.push_back(student("email" + std::to_string(i), "G" + std::to_string(i % 7), i * 97 % 10001));
    V4Index randomized(rows);
    for (int step = 0; step < 2000; ++step) {
        const auto index = rng() % rows.size();
        const auto group = "G" + std::to_string(rng() % 12);
        assert(randomized.change_group(rows[index].m_email, group));
        rows[index].m_group = group;
        if (step % 25 == 0) {
            assert(randomized.validate());
            assert(randomized.largest_groups() == reference(rows, false));
            assert(randomized.highest_average_groups() == reference(rows, true));
        }
    }

    auto actual = read_students(argv[1]);
    assert(actual.size() == 100000);
    V4Index full(actual);
    assert(full.validate());
    assert(full.largest_groups() == reference(actual, false));
    assert(full.highest_average_groups() == reference(actual, true));
    for (int i = 0; i < 10; ++i) {
        const auto group = "TEST-" + std::to_string(i % 3);
        assert(full.change_group(actual[i].m_email, group));
        actual[i].m_group = group;
    }
    assert(full.validate());
    assert(full.largest_groups() == reference(actual, false));
    assert(full.highest_average_groups() == reference(actual, true));
    std::cout << "V4 correctness tests passed\n";
}
