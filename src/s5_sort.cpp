#include "s5_sort.hpp"

#include <algorithm>
#include <array>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <stdexcept>

void standard_group_sort(std::vector<Student>& students) {
    std::sort(students.begin(), students.end(), [](const Student& a, const Student& b) {
        return a.m_group < b.m_group;
    });
}

void radix_group_sort(std::vector<Student>& students) {
    // S5 groups have fixed format AAA-00. ASCII order on these uppercase/digit
    // positions is the required ascending group order. The hyphen is constant.
    for (const auto& s : students) {
        const auto& g = s.m_group;
        if (g.size() != 6 || g[3] != '-' ||
            !std::all_of(g.begin(), g.begin() + 3, [](char c) { return c >= 'A' && c <= 'Z'; }) ||
            !std::all_of(g.begin() + 4, g.end(), [](char c) { return c >= '0' && c <= '9'; }))
            throw std::runtime_error("Invalid group for S5 radix sort: " + g);
    }
    const std::size_t n = students.size();
    std::vector<std::size_t> order(n), next(n);
    std::iota(order.begin(), order.end(), 0);
    for (int position : {5, 4, 2, 1, 0}) {
        std::array<std::size_t, 256> counts{};
        for (std::size_t i : order) ++counts[static_cast<unsigned char>(students[i].m_group[position])];
        std::size_t prefix = 0;
        for (auto& count : counts) {
            std::size_t current = count;
            count = prefix;
            prefix += current;
        }
        for (std::size_t i : order) next[counts[static_cast<unsigned char>(students[i].m_group[position])]++] = i;
        order.swap(next);
    }
    std::vector<Student> sorted;
    sorted.reserve(n);
    for (std::size_t i : order) sorted.push_back(std::move(students[i]));
    students.swap(sorted);
}

namespace {
void csv_string(std::ostream& out, const std::string& value) {
    const bool quote = value.find_first_of(",\"\r\n") != std::string::npos;
    if (quote) out << '"';
    for (char c : value) {
        if (c == '"') out << '"';
        out << c;
    }
    if (quote) out << '"';
}
}

void write_students(const std::string& path, const std::vector<Student>& students) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write " + path);
    out << "m_name,m_surname,m_email,m_birth_year,m_birth_month,m_birth_day,m_group,m_rating,m_phone_number\n";
    for (const auto& s : students) {
        csv_string(out, s.m_name); out << ',';
        csv_string(out, s.m_surname); out << ',';
        csv_string(out, s.m_email); out << ',';
        out << s.m_birth_year << ',' << s.m_birth_month << ',' << s.m_birth_day << ',';
        csv_string(out, s.m_group); out << ',';
        out << s.rating_cents / 100 << '.' << std::setw(2) << std::setfill('0') << s.rating_cents % 100 << std::setfill(' ') << ',';
        csv_string(out, s.m_phone_number); out << '\n';
    }
    if (!out) throw std::runtime_error("Failed writing " + path);
}
