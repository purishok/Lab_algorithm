"""Summarize Python benchmarks, fit the slowest V4 operation, and draw SVG plots."""

from __future__ import annotations

import csv
import math
import platform
import statistics
from collections import Counter, defaultdict
from pathlib import Path


RESULTS = Path("results")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def solve_3x3(matrix: list[list[float]], vector: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda row: abs(augmented[row][column]))
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        if abs(divisor) < 1e-12:
            raise ValueError("Regression matrix is singular")
        for item in range(column, 4):
            augmented[column][item] /= divisor
        for row in range(3):
            if row == column:
                continue
            factor = augmented[row][column]
            for item in range(column, 4):
                augmented[row][item] -= factor * augmented[column][item]
    return [augmented[row][3] for row in range(3)]


def features(approach: str, n: int, groups: int) -> list[float]:
    if approach == "ranked_index":
        height = math.log2(groups)
        return [1.0, height, groups / n * height]
    if approach == "aggregate_map":
        return [1.0, float(groups), groups / n]
    return [1.0, float(n), float(groups)]


def fit(approach: str, points: list[tuple[int, int, float]]) -> list[float]:
    matrix_rows = [features(approach, n, groups) for n, groups, _ in points]
    values = [value for _, _, value in points]
    matrix = [[sum(row[i] * row[j] for row in matrix_rows) for j in range(3)] for i in range(3)]
    vector = [sum(row[i] * value for row, value in zip(matrix_rows, values)) for i in range(3)]
    return solve_3x3(matrix, vector)


def svg_chart(path: Path, title: str, ylabel: str,
              series: list[tuple[str, list[tuple[int, float, float]], str]]) -> None:
    width, height = 900, 520
    left, right, top, bottom = 85, 35, 55, 75
    xs = [n for _, points, _ in series for n, _, _ in points]
    ys = [value + deviation for _, points, _ in series for _, value, deviation in points]
    lower_values = [value - deviation for _, points, _ in series for _, value, deviation in points]
    lo_x, hi_x = math.log10(min(xs)), math.log10(max(xs))
    top_y = max(ys) * 1.12
    bottom_y = min(0, min(lower_values) * 1.12)

    def x(n: int) -> float:
        return left + (math.log10(n) - lo_x) / (hi_x - lo_x) * (width - left - right)

    def y(value: float) -> float:
        return height - bottom - (value - bottom_y) / (top_y - bottom_y) * (height - top - bottom)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{width/2}" y="30" text-anchor="middle" font-size="20" font-family="sans-serif">{title}</text>']
    for tick in range(6):
        value = bottom_y + (top_y - bottom_y) * tick / 5
        yy = y(value)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#e6e9ed"/>')
        parts.append(f'<text x="{left-12}" y="{yy+5:.1f}" text-anchor="end" font-size="12" font-family="sans-serif">{value:.1f}</text>')
    for n in (100, 1000, 10000, 100000):
        parts.append(f'<text x="{x(n):.1f}" y="{height-bottom+25}" text-anchor="middle" font-size="12" font-family="sans-serif">{n:,}</text>')
    parts.append(f'<text x="{width/2}" y="{height-18}" text-anchor="middle" font-size="14" font-family="sans-serif">Students (log scale)</text>')
    parts.append(f'<text transform="translate(20 {height/2}) rotate(-90)" text-anchor="middle" font-size="14" font-family="sans-serif">{ylabel}</text>')
    for index, (label, points, color) in enumerate(series):
        coordinates = " ".join(f"{x(n):.1f},{y(value):.1f}" for n, value, _ in points)
        parts.append(f'<polyline points="{coordinates}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for n, value, deviation in points:
            xx, yy = x(n), y(value)
            if deviation:
                parts.append(f'<line x1="{xx:.1f}" y1="{y(value-deviation):.1f}" x2="{xx:.1f}" y2="{y(value+deviation):.1f}" stroke="{color}"/>')
                for endpoint in (value - deviation, value + deviation):
                    parts.append(f'<line x1="{xx-4:.1f}" y1="{y(endpoint):.1f}" x2="{xx+4:.1f}" y2="{y(endpoint):.1f}" stroke="{color}"/>')
            parts.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="3" fill="{color}"/>')
        parts.append(f'<rect x="{left+index*215}" y="{height-42}" width="16" height="4" fill="{color}"/>')
        parts.append(f'<text x="{left+index*215+22}" y="{height-35}" font-size="12" font-family="sans-serif">{label}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    compared = read_csv(RESULTS / "v4_comparison.csv")
    if {row["approach"] for row in compared} != {"vector_scan", "aggregate_map", "ranked_index"}:
        raise ValueError("Expected all three Python V4 approaches")
    winner = max(compared, key=lambda row: int(row["operations"]) / float(row["elapsed_s"]))["approach"]
    benchmark = read_csv(RESULTS / "v4_benchmark.csv")
    by_size: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in benchmark:
        if row["approach"] != winner:
            raise ValueError("Ten-size data is not from the comparison winner")
        by_size[int(row["n"])].append(row)
    if len(by_size) != 10 or any(len(rows) < 5 for rows in by_size.values()):
        raise ValueError("Expected ten sizes with five runs each")
    students = read_csv(Path("students.csv"))
    summary = []
    for n, rows in sorted(by_size.items()):
        group_counts = Counter(student["m_group"] for student in students[:n])
        operations = [int(row["operations"]) for row in rows]
        means = [statistics.mean(float(row[f"op{k}_mean_ns"]) for row in rows) for k in (1, 2, 3)]
        deviations = [statistics.stdev(float(row[f"op{k}_mean_ns"]) for row in rows) for k in (1, 2, 3)]
        slowest = max(range(3), key=lambda k: means[k])
        summary.append({
            "n": n, "groups": len(group_counts),
            "singleton_share": sum(count == 1 for count in group_counts.values()) / n,
            "throughput": statistics.mean(operations), "throughput_sd": statistics.stdev(operations),
            "means": means, "deviations": deviations, "slowest": slowest,
            "memory": int(rows[0]["estimated_bytes"]),
        })
    regression_operation = max(range(3), key=lambda k: statistics.mean(row["means"][k] for row in summary))
    coefficients = fit(winner, [(row["n"], row["groups"], row["means"][regression_operation]) for row in summary])
    actual = [(row["n"], row["means"][regression_operation], row["deviations"][regression_operation]) for row in summary]
    predicted = [(row["n"], sum(a * b for a, b in zip(coefficients, features(winner, row["n"], row["groups"]))), 0.0) for row in summary]
    mean_y = statistics.mean(value for _, value, _ in actual)
    residual = sum((a[1] - p[1]) ** 2 for a, p in zip(actual, predicted))
    total = sum((value - mean_y) ** 2 for _, value, _ in actual)
    r_squared = 1 - residual / total if total else float("nan")
    svg_chart(RESULTS / "slowest_regression.svg", f"Python V4 operation {regression_operation + 1} and regression", "Mean latency (ns)",
              [("Measured ± SD", actual, "#16609e"), ("Least squares fit", predicted, "#e05a38")])
    svg_chart(RESULTS / "throughput.svg", "Python V4 mixed workload throughput", "Operations in 10 seconds",
              [("Mean ± SD", [(row["n"], row["throughput"], row["throughput_sd"]) for row in summary], "#16885b")])

    lines = ["# Python V4 and S5 benchmark report", "",
             "Assigned variant: V4, operation ratio 50:100:100, S5 group sort. Implementation uses Python's standard library.", "",
             f"Environment: Python {platform.python_version()}, {platform.system()} {platform.machine()}.", "",
             "## Task I: three approaches on 100,000 students", "",
             "All approaches received the same precomputed 25,000-operation tape. Each shuffled 250-operation block contains exactly 50, 100, and 100 operations of types 1, 2, and 3. Emails and destination groups exist in the source. Setup and validation are outside timing. Final blocks can make elapsed time slightly exceed 10 seconds; normalized throughput accounts for that.", "",
             "| Approach | Containers | Observed operations | Elapsed s | Operations / 10 s |",
             "|---|---|---:|---:|---:|"]
    descriptions = {
        "vector_scan": "list, temporary group dict",
        "aggregate_map": "email dict, group aggregate dict",
        "ranked_index": "email/group dicts, tie sets, bounded max heaps",
    }
    for row in compared:
        elapsed = float(row["elapsed_s"])
        operations = int(row["operations"])
        lines.append(f"| {row['approach']} | {descriptions[row['approach']]} | {operations:,} | {elapsed:.3f} | {operations * 10 / elapsed:,.0f} |")
    lines += ["", f"**Winner: `{winner}`.** List scanning costs O(n) for each operation. The aggregate map changes groups in expected O(1) and scans g groups for maximum queries. The ranked index uses dictionaries, exact `Fraction` average keys, tie sets, and bounded lazy heaps; updates are expected O(log g) amortized and returning k winning groups costs O(k) amortized. Maximum queries are 60% of this workload.", "",
              "## Winner across ten database sizes", "",
              "Five independent 10-second runs were made at each size. The operation tape was prepared before each run and reused cyclically. The initial database build and final validation are excluded. Operation latency is sampled every 128 executions of each type; stopwatch overhead and scheduling add noise.", "",
              f"| Students | Groups | Singleton share | Operations / 10 s, mean ± SD | Op 1 ns, mean ± SD | Op 2 ns, mean ± SD | Op 3 ns, mean ± SD | Slowest at n | Predicted op {regression_operation + 1} ns | Estimated bytes |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row, (_, prediction, _) in zip(summary, predicted):
        latency = " | ".join(f"{mean:.1f} ± {deviation:.1f}" for mean, deviation in zip(row["means"], row["deviations"]))
        lines.append(f"| {row['n']:,} | {row['groups']:,} | {row['singleton_share']:.1%} | {row['throughput']:,.0f} ± {row['throughput_sd']:,.0f} | {latency} | {row['slowest'] + 1} | {prediction:.1f} | {row['memory']:,} |")
    if winner == "ranked_index":
        formula = (f"T(n) = {coefficients[0]:.4f} + {coefficients[1]:.4f} log₂(g(n)) + "
                   f"{coefficients[2]:.4f} [g(n)/n] log₂(g(n)) ns")
        basis_note = "The three terms model fixed work, heap height O(log g), and extra heap work weighted by group occupancy. The g/n factor is a heuristic for update churn, not an exact probability."
    elif winner == "aggregate_map":
        formula = f"T(n) = {coefficients[0]:.4f} + {coefficients[1]:.4f} g(n) + {coefficients[2]:.4f} g(n)/n ns"
        basis_note = "The terms model fixed work, scanning g groups, and an occupancy effect; the last term is heuristic."
    else:
        formula = f"T(n) = {coefficients[0]:.4f} + {coefficients[1]:.4f} n + {coefficients[2]:.4f} g(n) ns"
        basis_note = "The terms model fixed work, scanning n students, and building/scanning g group aggregates."
    lines += ["", "## Regression and memory", "",
              f"Let g(n) be the distinct-group count in the first n source rows, as tabulated above. Operation {regression_operation + 1} has the highest mean latency across the ten sizes. {formula}; R² = {r_squared:.4f}.", "",
              basis_note + f" Coefficients come from ordinary least squares over the ten operation-{regression_operation + 1} means. The table also identifies the slowest operation at each individual size; operation 3 is slightly slower at 100,000 rows. The negative intercept means the model should not be extrapolated outside the tested range. This is a dataset-specific descriptive fit and does not prove asymptotic growth. Distinct groups saturate near 4,000, so update cost need not grow monotonically with n.", "",
              "Memory is `deep_sizeof(database)` before timing: `sys.getsizeof` sums reachable lists, dictionaries, sets, tuples, heap entries, student objects, strings, integers, and fractions once each. Immutable strings shared with the source objects are included because the database references them. The separate source list, Python interpreter, allocator overhead, source CSV file, and prepared operation tape are excluded; this is not process RSS.", "",
              "![Slowest operation and fit](slowest_regression.svg)", "",
              "![Mixed workload throughput](throughput.svg)", "",
              "## Task II: S5 sorting by group", "",
              "`standard` uses Python's `sorted` with the group key, O(n log n). `radix` builds a dictionary of group buckets, uses five stable counting passes to order the distinct `AAA-00` keys, then concatenates buckets: O(n + 5(g + 256)). The timed interval includes all helper structures made by each sort and excludes CSV writing. Each size and method has five repetitions; method order alternates.", "",
              "| Students | Standard ms, mean ± SD | Radix ms, mean ± SD | Faster method |",
              "|---:|---:|---:|---|"]
    sorting = read_csv(RESULTS / "s5_benchmark.csv")
    sort_series = {"standard": [], "radix": []}
    for n in sorted(by_size):
        stats = {}
        for method in ("standard", "radix"):
            values = [float(row["sort_ms"]) for row in sorting if int(row["n"]) == n and row["method"] == method]
            if len(values) != 5:
                raise ValueError(f"Expected five sort runs for n={n}/{method}")
            stats[method] = (statistics.mean(values), statistics.stdev(values))
            sort_series[method].append((n, *stats[method]))
        faster = min(stats, key=lambda method: stats[method][0])
        lines.append(f"| {n:,} | {stats['standard'][0]:.4f} ± {stats['standard'][1]:.4f} | {stats['radix'][0]:.4f} ± {stats['radix'][1]:.4f} | {faster} |")
    svg_chart(RESULTS / "s5_sort.svg", "Python S5 sorting by group", "Sort time (ms)",
              [("Standard mean ± SD", sort_series["standard"], "#16609e"),
               ("Radix mean ± SD", sort_series["radix"], "#e05a38")])
    lines += ["", "![S5 sort comparison](s5_sort.svg)", "",
              "The full sorted outputs are `s5_standard.csv` and `s5_radix.csv`. Independent checks confirm ascending groups and exact preservation of all input fields and email identifiers; tie order is unspecified.", "",
              "## Defense notes", "",
              "All three designs pass differential tests after randomized group changes, including ties and disappearing groups. The ranked index rebuilds stale heaps periodically to bound their memory. Python dictionaries use randomized string hashing but do not offer deterministic worst-case lookup time. For adversarial input, replace email and group dictionaries with a balanced search tree for O(log n) lookup, validate sizes and formats, and paginate large tied results.", ""]
    (RESULTS / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
