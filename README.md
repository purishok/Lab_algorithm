# Homework 1: sorting and data structures

Assigned student: **Михайло Степанюк**, ПСА25/Б-1. The assignment spreadsheet (row 90) gives Task I variant **V4**, workload ratio **50:100:100**, and Task II variant **S5** (ascending `m_group`). The instructor confirmed that AI may complete the whole lab, superseding the narrower AI-use wording in the supplied PDF.

## What is implemented

Task I has three C++17 designs with the same operations:

| Design | Main containers | Maximum queries | Email change |
|---|---|---|---|
| `V4Vector` | Student vector; temporary hash aggregates | O(n) scan | O(n) scan |
| `V4AggregateMap` | Email hash plus ordered map of group counts and sums | O(g) group scan | Expected O(1) lookup + O(log g) update |
| `V4Index` | Email hash plus two ordered group rankings | O(k) for k tied groups | Expected O(1) lookup + O(log g) update |

For the assigned ratio, `V4Index` won the 10 second comparison on 100,000 students. Its ten-size experiment uses five independent 10 second runs per size from 100 to 100,000 students. The report includes throughput, mean and standard deviation for each operation, a memory estimate, regression with a plotted fit, and a discussion of the nonmonotone measurements. All mutation-sensitive answers use exact integer-cent sums for averages.

Task II uses `std::sort` and a custom stable least-significant-digit radix sort over the five varying characters of each `AAA-00` group key. Both methods export all 100,000 students to separate sorted CSVs. Sort timing excludes input duplication and CSV writing but includes all helper structures created inside the sort. Five timings per method and size are reported for ten database sizes. Full-output checks verified sorted order and preservation of every email identifier.

## Build, test, and reproduce

Requires Make, a C++17 compiler, and Python 3 with only its standard library.

```sh
make test
make build/demo_v4
./build/demo_v4 students.csv
make compare
make benchmark
make sort-benchmark
python3 analyze.py
make verify-results
```

The interactive demo accepts `count`, `move EMAIL GROUP`, `average`, and `quit`. The Task I comparison takes about 30 seconds. The winner's full experiment takes about 500 seconds (10 sizes × 5 repetitions × 10 seconds). `results/REPORT.md` contains tables, model details, plots, and defense notes. The raw timings are `results/v4_comparison.csv`, `results/v4_benchmark.csv`, and `results/s5_benchmark.csv`. The full S5 exports are `results/s5_standard.csv` and `results/s5_radix.csv`.

The prepared mixed workload chooses existing student emails and existing destination groups, randomizes operation order in the required ratio, and repeats its tape during timing. Database initialization, operation preparation, final consistency checks, and CSV output are outside their respective timed intervals.

## Defense and limitations

For a hostile input or DoS setting, replace both email and group hash tables with balanced trees (`std::map`) for worst-case logarithmic lookup. Keep the balanced group rankings, validate input size and group format, and paginate a very large tied result. In the supplied dataset, distinct groups saturate near 4,000 and singleton groups become rare as n grows; this explains why operation 2 does not simply increase with n. The regression is a descriptive fit to the measured range (R² shown in the report), not a proof of asymptotic growth. The memory figure estimates container-owned storage and may count inline short-string capacity; it is not process RSS.

## Submission

The implementation and experiments are complete for the assigned variants. Before submitting, run `make test` on your own machine, read `results/REPORT.md`, and be ready to explain the three data structures, correctness after a `move`, timing boundaries, regression terms, radix passes, and DoS tradeoffs. Submit the GitHub repository URL, plus any report/archive required by your course portal. The PDF does not specify the portal or upload format, so confirm that with your instructor. Disclose AI assistance in accordance with the instructor's direct permission.
