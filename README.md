# Homework 1: sorting and data structures

Assigned student: **Михайло Степанюк**, ПСА25/Б-1. Spreadsheet row 90 assigns Task I **V4**, operation ratio **50:100:100**, and Task II **S5** (ascending `m_group`). The teacher confirmed Python and full AI assistance are allowed, despite the narrower wording in the supplied PDF.

This repository uses **Python 3.10+ and only the standard library**. The implementations are in [`src/lab.py`](src/lab.py); benchmark and demo commands are in [`src/benchmark.py`](src/benchmark.py). No C++ source or build step is required.

## Task I: three V4 designs

| Design | Containers | Maximum queries | Group change by email |
|---|---|---|---|
| `VectorScan` | Student list; aggregate map rebuilt for each query | O(n + g) | O(n) |
| `AggregateMap` | Email dictionary and group aggregate dictionary | O(g) | Expected O(1) |
| `RankedIndex` | Email/group dictionaries, tie sets, bounded max heaps | O(k) amortized for k winning groups | Expected O(log g) amortized |

`RankedIndex` won the 10-second comparison on 100,000 students. Its heaps can contain stale ranking keys after updates; a periodic heap rebuild bounds their size. A result with many tied groups takes time proportional to the number returned. Integer cents and exact fractions keep average ties correct.

The winner was measured for **ten sizes from 100 to 100,000, five 10-second runs per size**. The 50:100:100 operation tape is randomized in blocks, prepared before timing, and uses existing emails and destination groups. The report includes operation counts, individual mean operation times, standard deviations, a Python object-memory estimate, regression, and graphs.

## Task II: S5 sorting

The standard method uses Python's `sorted(..., key=m_group)`. The custom method groups records in buckets, radix-sorts the distinct fixed-format `AAA-00` group keys using five stable counting passes, then concatenates buckets. Both write complete sorted CSVs: `results/s5_standard.csv` and `results/s5_radix.csv`. Timings at ten sizes have five repetitions per method. CSV writing is outside sort timing; bucket and radix helper structures are inside it.

## Run and verify

From the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_lab.py' -v
python3 tests/verify_outputs.py
python3 -m src.benchmark demo
```

The demo accepts `count`, `move EMAIL GROUP`, `average`, and `quit`. To reproduce all measurements and generated files:

```sh
python3 -m src.benchmark compare
python3 -m src.benchmark winner
python3 -m src.benchmark sort
python3 analyze.py
python3 tests/verify_outputs.py
```

The comparison takes about 30 seconds. The winner experiment takes about 500 seconds. `results/REPORT.md` contains the tables, plots, regression function, method details, and defense notes. Raw measurements are in the three benchmark CSVs.

## Defense and limitations

The indexed design suits a workload with 60% maximum queries. Updates maintain group counts, exact rating sums, and the two rankings. Tests compare all three designs to an independent calculation after random group moves, including ties and disappearing groups. For adversarial input, Python dictionaries have no deterministic worst-case lookup guarantee; use a balanced search tree for email and group indexes, constrain inputs, and paginate a huge tied result. The memory number counts reachable Python objects with `sys.getsizeof` once each; it excludes interpreter and allocator overhead, so it is not process RSS. The regression describes these ten dataset prefixes and is not a proof of asymptotic growth.

## Submission

Run the tests, read `results/REPORT.md`, and be ready to explain all three designs, the timing boundaries, group updates, regression, radix passes, and DoS tradeoffs. Submit the GitHub repository URL and any report/archive your course portal requires. The PDF does not specify the portal or upload format, so confirm that detail with the teacher. Disclose AI assistance according to the teacher's permission.
