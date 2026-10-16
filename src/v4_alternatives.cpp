#include "v4_alternatives.hpp"

#include <algorithm>
#include <stdexcept>

namespace {
struct Aggregate { std::int64_t cents{}; std::size_t count{}; };

template <typename Groups>
std::vector<std::string> largest(const Groups& groups) {
    std::vector<std::string> answer;
    std::size_t best = 0;
    for (const auto& [name, a] : groups) {
        if (a.count > best) { best = a.count; answer = {name}; }
        else if (a.count == best) answer.push_back(name);
    }
    std::sort(answer.begin(), answer.end());
    return answer;
}

template <typename Groups>
std::vector<std::string> highest_average(const Groups& groups) {
    std::vector<std::string> answer;
    std::int64_t best_cents = 0;
    std::size_t best_count = 1;
    for (const auto& [name, a] : groups) {
        const auto lhs = a.cents * static_cast<std::int64_t>(best_count);
        const auto rhs = best_cents * static_cast<std::int64_t>(a.count);
        if (answer.empty() || lhs > rhs) {
            best_cents = a.cents;
            best_count = a.count;
            answer = {name};
        } else if (lhs == rhs) answer.push_back(name);
    }
    std::sort(answer.begin(), answer.end());
    return answer;
}
}

std::vector<std::string> V4Vector::largest_groups() const {
    std::unordered_map<std::string, Aggregate> groups;
    for (const auto& s : students_) ++groups[s.m_group].count;
    return largest(groups);
}

bool V4Vector::change_group(const std::string& email, const std::string& new_group) {
    for (auto& s : students_) {
        if (s.m_email == email) { s.m_group = new_group; return true; }
    }
    return false;
}

std::vector<std::string> V4Vector::highest_average_groups() const {
    std::unordered_map<std::string, Aggregate> groups;
    for (const auto& s : students_) {
        auto& a = groups[s.m_group];
        ++a.count;
        a.cents += s.rating_cents;
    }
    return highest_average(groups);
}

V4AggregateMap::V4AggregateMap(std::vector<Student> students) : students_(std::move(students)) {
    by_email_.reserve(students_.size());
    for (std::size_t i = 0; i < students_.size(); ++i) {
        const auto& s = students_[i];
        if (!by_email_.emplace(s.m_email, i).second) throw std::runtime_error("Duplicate email: " + s.m_email);
        auto& a = groups_[s.m_group];
        ++a.count;
        a.cents += s.rating_cents;
    }
}

std::vector<std::string> V4AggregateMap::largest_groups() const { return largest(groups_); }

bool V4AggregateMap::change_group(const std::string& email, const std::string& new_group) {
    auto found = by_email_.find(email);
    if (found == by_email_.end()) return false;
    auto& s = students_[found->second];
    if (s.m_group == new_group) return true;
    auto old = groups_.find(s.m_group);
    --old->second.count;
    old->second.cents -= s.rating_cents;
    if (old->second.count == 0) groups_.erase(old);
    auto& target = groups_[new_group];
    ++target.count;
    target.cents += s.rating_cents;
    s.m_group = new_group;
    return true;
}

std::vector<std::string> V4AggregateMap::highest_average_groups() const { return highest_average(groups_); }

bool V4AggregateMap::validate() const {
    std::map<std::string, Aggregate> expected;
    for (std::size_t i = 0; i < students_.size(); ++i) {
        const auto& s = students_[i];
        auto it = by_email_.find(s.m_email);
        if (it == by_email_.end() || it->second != i) return false;
        auto& a = expected[s.m_group];
        ++a.count;
        a.cents += s.rating_cents;
    }
    if (expected.size() != groups_.size()) return false;
    for (const auto& [name, a] : expected) {
        auto it = groups_.find(name);
        if (it == groups_.end() || it->second.count != a.count || it->second.cents != a.cents) return false;
    }
    return true;
}
