#pragma once

#include <cstddef>
#include <cstdint>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

struct Student {
    std::string m_name, m_surname, m_email;
    int m_birth_year{}, m_birth_month{}, m_birth_day{};
    std::string m_group;
    float m_rating{};
    std::string m_phone_number;
    int rating_cents{}; // Exact aggregate arithmetic for ratings with two decimal places.
};

std::vector<Student> read_students(const std::string& path, std::size_t limit = 100000);

class V4Index {
public:
    explicit V4Index(std::vector<Student> students);
    std::vector<std::string> largest_groups() const;
    bool change_group(const std::string& email, const std::string& new_group);
    std::vector<std::string> highest_average_groups() const;
    const std::vector<Student>& students() const { return students_; }
    std::vector<std::string> groups() const;
    std::size_t estimated_bytes() const;
    bool validate() const;

private:
    struct Aggregate { std::int64_t cents{}; std::size_t count{}; };
    struct CountKey { std::size_t count; std::string group; };
    struct AverageKey { std::int64_t cents; std::size_t count; std::string group; };
    struct CountLess {
        bool operator()(const CountKey& a, const CountKey& b) const;
    };
    struct AverageLess {
        bool operator()(const AverageKey& a, const AverageKey& b) const;
    };
    void remove_ranks(const std::string& group, Aggregate a);
    void add_ranks(const std::string& group, Aggregate a);

    std::vector<Student> students_;
    std::unordered_map<std::string, std::size_t> by_email_;
    std::unordered_map<std::string, Aggregate> aggregates_;
    std::set<CountKey, CountLess> by_count_;
    std::set<AverageKey, AverageLess> by_average_;
};
