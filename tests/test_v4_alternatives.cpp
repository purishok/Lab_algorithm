#include "v4_alternatives.hpp"

#include <algorithm>
#include <cassert>
#include <iostream>
#include <map>
#include <random>

using Groups = std::map<std::string, std::pair<std::int64_t, std::size_t>>;

static std::pair<std::vector<std::string>, std::vector<std::string>> reference(const std::vector<Student>& rows) {
    Groups groups;
    for (const auto& s : rows) {
        auto& a = groups[s.m_group];
        a.first += s.rating_cents;
        ++a.second;
    }
    std::vector<std::string> count, average;
    std::size_t max_count = 0;
    std::int64_t best_sum = 0;
    std::size_t best_count = 1;
    for (const auto& [name, a] : groups) {
        if (a.second > max_count) { max_count = a.second; count = {name}; }
        else if (a.second == max_count) count.push_back(name);
        auto left = a.first * static_cast<std::int64_t>(best_count);
        auto right = best_sum * static_cast<std::int64_t>(a.second);
        if (average.empty() || left > right) { best_sum = a.first; best_count = a.second; average = {name}; }
        else if (left == right) average.push_back(name);
    }
    return {count, average};
}

template <typename Database>
static void check(Database& db, const std::vector<Student>& rows) {
    auto [count, average] = reference(rows);
    assert(db.largest_groups() == count);
    assert(db.highest_average_groups() == average);
    assert(db.validate());
}

int main(int argc, char** argv) {
    assert(argc == 2);
    auto all = read_students(argv[1]);
    std::vector<Student> rows(all.begin(), all.begin() + 1000);
    V4Vector vector(rows);
    V4AggregateMap map(rows);
    V4Index ranked(rows);
    check(vector, rows); check(map, rows); check(ranked, rows);
    assert(!vector.change_group("missing@email", "NEW-01"));
    assert(!map.change_group("missing@email", "NEW-01"));
    assert(!ranked.change_group("missing@email", "NEW-01"));
    std::mt19937 rng(442);
    for (int step = 0; step < 1000; ++step) {
        std::size_t index = rng() % rows.size();
        std::string group = step % 7 == 0 ? "NEW-01" : "G" + std::to_string(rng() % 30);
        const auto email = rows[index].m_email;
        assert(vector.change_group(email, group));
        assert(map.change_group(email, group));
        assert(ranked.change_group(email, group));
        rows[index].m_group = group;
        if (step % 20 == 0) {
            check(vector, rows); check(map, rows); check(ranked, rows);
        }
    }
    check(vector, rows); check(map, rows); check(ranked, rows);
    std::cout << "All three V4 approaches passed differential tests\n";
}
