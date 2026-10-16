#pragma once

#include "v4_index.hpp"

#include <map>
#include <unordered_map>

// Approach A: one vector, with group aggregates built anew for each query.
class V4Vector {
public:
    explicit V4Vector(std::vector<Student> students) : students_(std::move(students)) {}
    std::vector<std::string> largest_groups() const;
    bool change_group(const std::string& email, const std::string& new_group);
    std::vector<std::string> highest_average_groups() const;
    const std::vector<Student>& students() const { return students_; }
    bool validate() const { return true; }

private:
    std::vector<Student> students_;
};

// Approach B: email hash lookup plus ordered map of group aggregates.
// Queries scan only groups, while updates change two map entries.
class V4AggregateMap {
public:
    explicit V4AggregateMap(std::vector<Student> students);
    std::vector<std::string> largest_groups() const;
    bool change_group(const std::string& email, const std::string& new_group);
    std::vector<std::string> highest_average_groups() const;
    const std::vector<Student>& students() const { return students_; }
    bool validate() const;

private:
    struct Aggregate { std::int64_t cents{}; std::size_t count{}; };
    std::vector<Student> students_;
    std::unordered_map<std::string, std::size_t> by_email_;
    std::map<std::string, Aggregate> groups_;
};
