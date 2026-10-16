#pragma once

#include "v4_index.hpp"

#include <string>
#include <vector>

void standard_group_sort(std::vector<Student>& students);
void radix_group_sort(std::vector<Student>& students);
void write_students(const std::string& path, const std::vector<Student>& students);
