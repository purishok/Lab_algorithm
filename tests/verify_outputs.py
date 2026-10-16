"""Independent checks for generated CSV outputs and benchmark completeness."""

import csv
from collections import Counter
from pathlib import Path


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    source = read(Path("students.csv"))
    assert len(source) == 100000
    by_email = {row["m_email"]: row for row in source}
    assert len(by_email) == len(source)
    for name in ("s5_standard.csv", "s5_radix.csv"):
        rows = read(Path("results") / name)
        assert len(rows) == len(source)
        assert Counter(row["m_email"] for row in rows) == Counter(by_email.keys())
        assert all(a["m_group"] <= b["m_group"] for a, b in zip(rows, rows[1:]))
        for row in rows:
            original = by_email[row["m_email"]]
            for key in row:
                if key == "m_rating":
                    assert float(row[key]) == float(original[key])
                else:
                    assert row[key] == original[key]

    comparison = read(Path("results/v4_comparison.csv"))
    assert {row["approach"] for row in comparison} == {"vector_scan", "aggregate_map", "ranked_index"}
    assert all(float(row["elapsed_s"]) >= 10 for row in comparison)
    winner = max(comparison, key=lambda row: int(row["operations"]) / float(row["elapsed_s"]))["approach"]
    benchmark = read(Path("results/v4_benchmark.csv"))
    sizes = [100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
    assert len(benchmark) == 50
    assert {row["approach"] for row in benchmark} == {winner}
    assert Counter(int(row["n"]) for row in benchmark) == Counter({n: 5 for n in sizes})
    assert all(float(row["elapsed_s"]) >= 10 for row in benchmark)
    for row in comparison + benchmark:
        total = int(row["operations"])
        counts = [int(row[f"op{k}_count"]) for k in (1, 2, 3)]
        assert sum(counts) == total
        assert all(abs(count / total - share) < 0.02 for count, share in zip(counts, (0.2, 0.4, 0.4)))
    sorting = read(Path("results/s5_benchmark.csv"))
    assert len(sorting) == 100
    assert Counter((int(row["n"]), row["method"]) for row in sorting) == Counter({(n, method): 5 for n in sizes for method in ("standard", "radix")})
    print("Sorted outputs preserve every field; all benchmark runs are present")


if __name__ == "__main__":
    main()
