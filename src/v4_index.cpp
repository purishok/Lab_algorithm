#include "v4_index.hpp"

#include <cmath>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace {
std::vector<std::string> csv_fields(const std::string& line) {
    std::vector<std::string> fields;
    std::string field;
    bool quoted = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        char c = line[i];
        if (c == '"') {
            if (quoted && i + 1 < line.size() && line[i + 1] == '"') {
                field += '"';
                ++i;
            } else {
                quoted = !quoted;
            }
        } else if (c == ',' && !quoted) {
            fields.push_back(std::move(field));
            field.clear();
        } else {
            field += c;
        }
    }
    if (quoted) throw std::runtime_error("Unclosed CSV quote");
    if (!field.empty() && field.back() == '\r') field.pop_back();
    fields.push_back(std::move(field));
    return fields;
}
}

std::vector<Student> read_students(const std::string& path, std::size_t limit) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("Cannot open " + path);
    std::string line;
    if (!std::getline(in, line)) throw std::runtime_error("Empty CSV");
    const std::vector<std::string> expected = {"m_name", "m_surname", "m_email", "m_birth_year", "m_birth_month", "m_birth_day", "m_group", "m_rating", "m_phone_number"};
    if (csv_fields(line) != expected) throw std::runtime_error("Unexpected CSV header");
    std::vector<Student> rows;
    rows.reserve(limit);
    while (rows.size() < limit && std::getline(in, line)) {
        auto f = csv_fields(line);
        if (f.size() != 9) throw std::runtime_error("Expected 9 CSV fields at row " + std::to_string(rows.size() + 2));
        Student s;
        s.m_name = std::move(f[0]); s.m_surname = std::move(f[1]); s.m_email = std::move(f[2]);
        s.m_birth_year = std::stoi(f[3]); s.m_birth_month = std::stoi(f[4]); s.m_birth_day = std::stoi(f[5]);
        s.m_group = std::move(f[6]); s.m_rating = std::stof(f[7]);
        s.rating_cents = static_cast<int>(std::lround(std::stod(f[7]) * 100.0));
        s.m_phone_number = std::move(f[8]);
        rows.push_back(std::move(s));
    }
    return rows;
}

bool V4Index::CountLess::operator()(const CountKey& a, const CountKey& b) const {
    return a.count != b.count ? a.count > b.count : a.group < b.group;
}

bool V4Index::AverageLess::operator()(const AverageKey& a, const AverageKey& b) const {
    const auto left = a.cents * static_cast<std::int64_t>(b.count);
    const auto right = b.cents * static_cast<std::int64_t>(a.count);
    return left != right ? left > right : a.group < b.group;
}

V4Index::V4Index(std::vector<Student> students) : students_(std::move(students)) {
    by_email_.reserve(students_.size());
    for (std::size_t i = 0; i < students_.size(); ++i) {
        const auto& s = students_[i];
        if (!by_email_.emplace(s.m_email, i).second) throw std::runtime_error("Duplicate email: " + s.m_email);
        auto& a = aggregates_[s.m_group];
        ++a.count;
        a.cents += s.rating_cents;
    }
    for (const auto& [group, a] : aggregates_) add_ranks(group, a);
}

void V4Index::remove_ranks(const std::string& group, Aggregate a) {
    by_count_.erase(CountKey{a.count, group});
    by_average_.erase(AverageKey{a.cents, a.count, group});
}

void V4Index::add_ranks(const std::string& group, Aggregate a) {
    by_count_.insert(CountKey{a.count, group});
    by_average_.insert(AverageKey{a.cents, a.count, group});
}

std::vector<std::string> V4Index::largest_groups() const {
    std::vector<std::string> result;
    if (by_count_.empty()) return result;
    const auto maximum = by_count_.begin()->count;
    for (auto it = by_count_.begin(); it != by_count_.end() && it->count == maximum; ++it) result.push_back(it->group);
    return result;
}

bool V4Index::change_group(const std::string& email, const std::string& new_group) {
    auto found = by_email_.find(email);
    if (found == by_email_.end()) return false;
    Student& student = students_[found->second];
    if (student.m_group == new_group) return true;
    const std::string old_group = student.m_group;
    auto old_it = aggregates_.find(old_group);
    remove_ranks(old_group, old_it->second);
    --old_it->second.count;
    old_it->second.cents -= student.rating_cents;
    if (old_it->second.count == 0) aggregates_.erase(old_it);
    else add_ranks(old_group, aggregates_.at(old_group));

    auto new_it = aggregates_.find(new_group);
    if (new_it != aggregates_.end()) remove_ranks(new_group, new_it->second);
    auto& target = aggregates_[new_group];
    ++target.count;
    target.cents += student.rating_cents;
    add_ranks(new_group, target);
    student.m_group = new_group;
    return true;
}

std::vector<std::string> V4Index::highest_average_groups() const {
    std::vector<std::string> result;
    if (by_average_.empty()) return result;
    const auto& first = *by_average_.begin();
    for (auto it = by_average_.begin(); it != by_average_.end(); ++it) {
        if (it->cents * static_cast<std::int64_t>(first.count) != first.cents * static_cast<std::int64_t>(it->count)) break;
        result.push_back(it->group);
    }
    return result;
}

std::vector<std::string> V4Index::groups() const {
    std::vector<std::string> result;
    result.reserve(aggregates_.size());
    for (const auto& [name, _] : aggregates_) result.push_back(name);
    return result;
}

std::size_t V4Index::estimated_bytes() const {
    // Approximate owned live heap allocations: vector capacity, string capacities,
    // hash bucket arrays and nodes, plus red-black-tree nodes. No allocator overhead.
    std::size_t bytes = students_.capacity() * sizeof(Student);
    for (const auto& s : students_) {
        bytes += s.m_name.capacity() + s.m_surname.capacity() + s.m_email.capacity();
        bytes += s.m_group.capacity() + s.m_phone_number.capacity();
    }
    bytes += by_email_.bucket_count() * sizeof(void*);
    for (const auto& [email, _] : by_email_) bytes += sizeof(void*) * 2 + sizeof(std::pair<const std::string, std::size_t>) + email.capacity();
    bytes += aggregates_.bucket_count() * sizeof(void*);
    for (const auto& [group, _] : aggregates_) {
        bytes += sizeof(void*) * 2 + sizeof(std::pair<const std::string, Aggregate>) + group.capacity();
        bytes += 3 * sizeof(void*) + sizeof(CountKey) + group.capacity();
        bytes += 3 * sizeof(void*) + sizeof(AverageKey) + group.capacity();
    }
    return bytes;
}

bool V4Index::validate() const {
    std::unordered_map<std::string, Aggregate> recalculated;
    for (std::size_t i = 0; i < students_.size(); ++i) {
        const auto& s = students_[i];
        auto email = by_email_.find(s.m_email);
        if (email == by_email_.end() || email->second != i) return false;
        auto& a = recalculated[s.m_group];
        ++a.count;
        a.cents += s.rating_cents;
    }
    if (recalculated.size() != aggregates_.size() || by_count_.size() != aggregates_.size() || by_average_.size() != aggregates_.size()) return false;
    for (const auto& [group, a] : recalculated) {
        auto found = aggregates_.find(group);
        if (found == aggregates_.end() || found->second.count != a.count || found->second.cents != a.cents) return false;
        if (!by_count_.count(CountKey{a.count, group}) || !by_average_.count(AverageKey{a.cents, a.count, group})) return false;
    }
    return true;
}
