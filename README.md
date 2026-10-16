# Homework 1: sorting and data structures

Assigned row: **Михайло Степанюк**, ПСА25/Б-1, Task I **V4**, operation ratio **50:100:100**, Task II **S5** (sort by `m_group`). Source: row 90 of `HW1_variants_2026.xlsx`.

## Submission status

This repository is **not yet a complete submission**. The PDF permits AI implementation of one Task I approach, linear regression, graphs, and automated tests. Accordingly, this repository contains one V4 approach and its experiments and tests. You must write and benchmark two more distinct Task I container approaches and both S5 sorting implementations yourself. You must also compare the two sorting times across database sizes. Do not submit this repository as a finished lab until those items are complete and reviewed.

## Included V4 approach

`src/v4_index.cpp` reads `students.csv` and keeps students in a vector. An email hash index locates the student to change. Two ordered sets rank nonempty groups by student count and exact average rating; each update removes and reinserts only the affected groups. Ratings are aggregated as integer cents, avoiding floating point errors when groups have equal averages.

For `g` nonempty groups and `k` tied winning groups, the count and average queries cost `O(k)` to return the result; moving a student costs expected `O(1)` email lookup plus `O(log g)` ordered set updates. Hash lookup is vulnerable to adversarial collisions, and a hostile user can cause many tied groups. For a DoS-resistant design, replace the email hash index with a balanced tree (`std::map`) for worst-case `O(log n)` lookup, retain balanced group rankings, bound input size, and consider output pagination for ties.

## Build and run

Requires a C++17 compiler, Make, and Python 3 standard library.

```sh
make test
make build/benchmark
mkdir -p results
./build/benchmark students.csv results/v4_benchmark.csv 10 5
python3 analyze.py
```

The benchmark takes about **500 seconds**: 10 sizes × 5 repetitions × 10 seconds. It excludes initial CSV reading and index construction from the 10 second workload. Queries and updates are randomly shuffled in the assigned 50:100:100 ratio. The prepared operation tape repeats to avoid generation time during measurement. The report and two SVG graphs are in `results/`.

## What you need to finish

1. Implement two more **distinct** V4 approaches using different containers. A straightforward baseline is a vector scan of students for each query; a second approach can use maps of group aggregates but scan the aggregates to find maxima. Explain their complexities and verify mutations. Benchmark all three approaches for 10 seconds each with the same operation tape and ratio, then identify the fastest.
2. If one of your approaches beats this implementation, run the 10-size, at-least-five-repetition experiment on that winner and update the regression, graph, and memory discussion accordingly.
3. Implement S5 twice: one using the language's standard sort, one using your own faster candidate such as bucket/radix sorting on the fixed-format group key. Include construction time for helper structures and exclude CSV write time from the sort timing. Export sorted students to CSV, compare sorting time across sizes, and check the output has every record in ascending `m_group` order.
4. Prepare to demonstrate correct queries after group changes, the measurement setup, why the chosen containers fit the ratio, and how a DoS-resistant version would differ.

## Submitting

After finishing the missing implementations, rerun tests and experiments on the machine used for the report. Check that `results/REPORT.md`, the plots, and your S5 outputs correspond to the final code. Commit and push the final files, then submit the GitHub repository URL **and** any report or archive required by your course platform. The PDF does not specify a course portal or exact upload format, so confirm those details with your instructor. Include an honest AI-use statement identifying the permitted parts assisted here.
