#include "s5_sort.hpp"

#include <algorithm>
#include <cassert>
#include <iostream>

static std::vector<std::string> emails(const std::vector<Student>& rows) {
    std::vector<std::string> result;
    result.reserve(rows.size());
    for (const auto& row : rows) result.push_back(row.m_email);
    std::sort(result.begin(), result.end());
    return result;
}

int main(int argc, char** argv) {
    assert(argc == 3);
    auto source = read_students(argv[1]);
    auto standard = source, radix = source;
    standard_group_sort(standard);
    radix_group_sort(radix);
    assert(std::is_sorted(standard.begin(), standard.end(), [](const Student& a, const Student& b) { return a.m_group < b.m_group; }));
    assert(std::is_sorted(radix.begin(), radix.end(), [](const Student& a, const Student& b) { return a.m_group < b.m_group; }));
    assert(emails(source) == emails(standard));
    assert(emails(source) == emails(radix));
    for (std::size_t i = 0; i < source.size(); ++i) assert(standard[i].m_group == radix[i].m_group);
    write_students(argv[2], radix);
    auto reread = read_students(argv[2]);
    assert(reread.size() == radix.size());
    for (std::size_t i = 0; i < radix.size(); ++i) {
        assert(reread[i].m_email == radix[i].m_email);
        assert(reread[i].m_group == radix[i].m_group);
        assert(reread[i].rating_cents == radix[i].rating_cents);
    }
    std::cout << "S5 sort and CSV round-trip tests passed\n";
}
