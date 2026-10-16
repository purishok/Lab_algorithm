"""Analyze measured V4 data with ordinary least squares and write SVG plots."""

import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


RESULTS = Path("results")


def solve_3x3(matrix, vector):
    a = [row[:] + [value] for row, value in zip(matrix, vector)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda row: abs(a[row][col]))
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        if abs(scale) < 1e-12:
            raise ValueError("Regression matrix is singular")
        for item in range(col, 4):
            a[col][item] /= scale
        for row in range(3):
            if row != col:
                factor = a[row][col]
                for item in range(col, 4):
                    a[row][item] -= factor * a[col][item]
    return [a[row][3] for row in range(3)]


def fit(points):
    # Three theory-motivated features: fixed work, tree height, and an
    # occupancy-weighted tree term for group deletion/recreation.
    features = [[1.0, math.log2(groups), groups / n * math.log2(groups)] for n, groups, value in points]
    y = [value for n, groups, value in points]
    matrix = [[sum(row[i] * row[j] for row in features) for j in range(3)] for i in range(3)]
    vector = [sum(row[i] * value for row, value in zip(features, y)) for i in range(3)]
    return solve_3x3(matrix, vector)


def svg_chart(path, title, ylabel, series, y_max=None):
    width, height = 900, 520
    left, right, top, bottom = 85, 35, 55, 75
    xs = [n for _, points, _ in series for n, _, _ in points]
    ys = [value + error for _, points, _ in series for _, value, error in points]
    lo_x, hi_x = math.log10(min(xs)), math.log10(max(xs))
    top_y = y_max or max(ys) * 1.12

    def x(n):
        return left + (math.log10(n) - lo_x) / (hi_x - lo_x) * (width - left - right)

    def y(value):
        return height - bottom - max(0, value) / top_y * (height - top - bottom)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="{width/2}" y="30" text-anchor="middle" font-size="20" font-family="sans-serif">{title}</text>']
    for tick in range(6):
        value = top_y * tick / 5
        yy = y(value)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#e6e9ed"/>')
        parts.append(f'<text x="{left-12}" y="{yy+5:.1f}" text-anchor="end" font-size="12" font-family="sans-serif">{value:.1f}</text>')
    for n in [100, 1000, 10000, 100000]:
        parts.append(f'<text x="{x(n):.1f}" y="{height-bottom+25}" text-anchor="middle" font-size="12" font-family="sans-serif">{n:,}</text>')
    parts.append(f'<text x="{width/2}" y="{height-18}" text-anchor="middle" font-size="14" font-family="sans-serif">Students (log scale)</text>')
    parts.append(f'<text transform="translate(20 {height/2}) rotate(-90)" text-anchor="middle" font-size="14" font-family="sans-serif">{ylabel}</text>')
    for index, (label, points, color) in enumerate(series):
        coords = " ".join(f"{x(n):.1f},{y(value):.1f}" for n, value, _ in points)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for n, value, error in points:
            xx, yy = x(n), y(value)
            if error:
                parts.append(f'<line x1="{xx:.1f}" y1="{y(value-error):.1f}" x2="{xx:.1f}" y2="{y(value+error):.1f}" stroke="{color}"/>')
                for end in (value - error, value + error):
                    parts.append(f'<line x1="{xx-4:.1f}" y1="{y(end):.1f}" x2="{xx+4:.1f}" y2="{y(end):.1f}" stroke="{color}"/>')
            parts.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="3" fill="{color}"/>')
        parts.append(f'<rect x="{left+index*205}" y="{height-42}" width="16" height="4" fill="{color}"/>')
        parts.append(f'<text x="{left+index*205+22}" y="{height-35}" font-size="12" font-family="sans-serif">{label}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts) + "\n")


def main():
    with (RESULTS / "v4_benchmark.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    by_size = defaultdict(list)
    for row in rows:
        by_size[int(row["n"])].append(row)
    if len(by_size) != 10 or any(len(group) < 5 for group in by_size.values()):
        raise ValueError("Expected 10 sizes and at least 5 repetitions per size")
    with Path("students.csv").open(newline="") as stream:
        students = list(csv.DictReader(stream))
    summary = []
    for n, group in sorted(by_size.items()):
        group_counts = defaultdict(int)
        for student in students[:n]:
            group_counts[student["m_group"]] += 1
        singleton_fraction = sum(count == 1 for count in group_counts.values()) / n
        operations = [int(row["operations"]) for row in group]
        means = [statistics.mean(float(row[f"op{k}_mean_ns"]) for row in group) for k in (1, 2, 3)]
        stds = [statistics.stdev(float(row[f"op{k}_mean_ns"]) for row in group) for k in (1, 2, 3)]
        slowest = max(range(3), key=lambda i: means[i])
        summary.append((n, statistics.mean(operations), statistics.stdev(operations), means, stds, slowest + 1, int(group[0]["estimated_bytes"]), len(group_counts), singleton_fraction))
    coefficients = fit([(n, group_count, means[slowest - 1]) for n, _, _, means, _, slowest, _, group_count, _ in summary])
    predicted = [(n, coefficients[0] + coefficients[1] * math.log2(group_count) + coefficients[2] * group_count / n * math.log2(group_count), 0) for n, _, _, _, _, _, _, group_count, _ in summary]
    actual = [(n, means[slowest - 1], stds[slowest - 1]) for n, _, _, means, stds, slowest, *_ in summary]
    fitted = {n: value for n, value, _ in predicted}
    observed = [value for _, value, _ in actual]
    total_error = sum((value - statistics.mean(observed)) ** 2 for value in observed)
    residual_error = sum((value - fitted[n]) ** 2 for n, value, _ in actual)
    r_squared = 1 - residual_error / total_error if total_error else float("nan")
    svg_chart(RESULTS / "slowest_regression.svg", "Slowest V4 operation and regression", "Mean latency (ns)", [("Measured ± SD", actual, "#16609e"), ("Least squares fit", predicted, "#e05a38")])
    svg_chart(RESULTS / "throughput.svg", "V4 mixed workload throughput", "Operations in 10 seconds", [("Mean ± SD", [(n, rate, sd) for n, rate, sd, *_ in summary], "#16885b")])
    c0, c_log, c_occupancy = coefficients
    lines = ["# V4 benchmark results", "", "Variant: V4, ratio 50:100:100. Each row averages five independent 10 second runs. The operation tape contains 25,000 randomly shuffled, preselected operations and repeats cyclically. Student emails and destination groups are chosen from existing values before timing. The initial index build and the final validation are outside the timed interval.", "", "| Students | Groups | Singleton share | Operations / 10 s, mean ± SD | Op 1 ns, mean ± SD | Op 2 ns, mean ± SD | Op 3 ns, mean ± SD | Slowest | Predicted T(n), ns | Estimated bytes |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for n, rate, sd, means, stds, slowest, memory, group_count, singleton_fraction in summary:
        latency = " | ".join(f"{mean:.1f} ± {sd_value:.1f}" for mean, sd_value in zip(means, stds))
        lines.append(f"| {n:,} | {group_count:,} | {singleton_fraction:.1%} | {rate:,.0f} ± {sd:,.0f} | {latency} | {slowest} | {fitted[n]:.1f} | {memory:,} |")
    lines += ["", "## Regression", "", f"Let g(n) be the number of distinct groups in the first n records (shown in the table). T(n) = {c0:.4f} + {c_log:.4f} log₂(g(n)) + {c_occupancy:.4f} [g(n)/n] log₂(g(n)) nanoseconds; R² = {r_squared:.4f}.", "", "The three basis functions represent fixed work, O(log g) balanced-tree updates, and extra O(log g) work weighted by group occupancy. The factor g/n is a coarse proxy for how often a move empties or recreates a group; it is not an exact probability. The fit is descriptive over this dataset, with a negative intercept outside the tested range. It does not prove asymptotic behavior. Group count saturates near 4,000 while singleton share falls to zero, so measured update time is not monotone in n. Latencies are sampled every 128 operations; timer overhead and operating-system scheduling contribute to variance.", "", "## Memory method", "", "`estimated_bytes()` sums vector capacity, string capacities, hash buckets and approximate nodes, and ordered-set nodes. This is a reproducible approximation, not process RSS: allocator metadata, code, stack, the prepared operation tape, and source CSV are excluded. Short strings may be stored inline, so counting their capacities can overstate heap use.", "", "![Slowest operation and fit](slowest_regression.svg)", "", "![Throughput](throughput.svg)", ""]

    with (RESULTS / "v4_comparison.csv").open(newline="") as stream:
        compared = list(csv.DictReader(stream))
    if {row["approach"] for row in compared} != {"vector_scan", "aggregate_map", "ranked_sets"}:
        raise ValueError("Expected all three V4 approaches")
    lines += ["## Three V4 approaches on 100,000 students", "", "All approaches used the same preselected 25,000-operation tape, shuffled in 250-operation blocks containing exactly 50:100:100 operations. Each approach ran for 10 seconds; reported throughput is normalized to exactly 10 seconds to account for the final block. Setup and post-run validation are excluded.", "", "| Approach | Main containers | Operations observed | Elapsed, s | Operations / 10 s |", "|---|---|---:|---:|---:|"]
    descriptions = {
        "vector_scan": "vector, temporary hash aggregates",
        "aggregate_map": "email hash + ordered group map",
        "ranked_sets": "email hash + two ordered group sets",
    }
    for row in compared:
        elapsed = float(row["elapsed_s"])
        operations = int(row["operations"])
        lines.append(f"| {row['approach']} | {descriptions[row['approach']]} | {operations:,} | {elapsed:.3f} | {operations * 10 / elapsed:,.0f} |")
    winner = max(compared, key=lambda row: int(row["operations"]) / float(row["elapsed_s"]))["approach"]
    lines += ["", f"**Winner: `{winner}`.** Vector queries and email changes scan n students: O(n) work per operation. The aggregate map finds an email in expected O(1), changes two groups in O(log g), and scans g group aggregates for each maximum query. Ranked sets find an email in expected O(1), update two ranking sets in O(log g), and return k tied groups in O(k). The weighted workload has 60% maximum queries, explaining the large ranked-set advantage at 100,000 rows. All three approaches pass differential tests after group changes.", "", "## S5: sorting by group", "", "`standard` sorts student records using `std::sort` and group comparisons, O(n log n). `radix` uses five stable counting passes over the nonconstant characters of the fixed `AAA-00` group key, then reorders records, O(5(n + 256)). The radix timing includes index arrays and all counting passes. Both methods sort a copied input; copying and CSV writing are outside the measured sort time. Each point uses five repetitions; method order alternates across repetitions.", "", "| Students | Standard ms, mean ± SD | Radix ms, mean ± SD | Faster method |", "|---:|---:|---:|---|"]
    with (RESULTS / "s5_benchmark.csv").open(newline="") as stream:
        sorting = list(csv.DictReader(stream))
    sort_series = {"standard": [], "radix": []}
    for n in sorted(by_size):
        stats = {}
        for method in ("standard", "radix"):
            values = [float(row["sort_ms"]) for row in sorting if int(row["n"]) == n and row["method"] == method]
            if len(values) != 5:
                raise ValueError(f"Expected five S5 samples for {n}/{method}")
            stats[method] = (statistics.mean(values), statistics.stdev(values))
            sort_series[method].append((n, *stats[method]))
        faster = min(stats, key=lambda method: stats[method][0])
        lines.append(f"| {n:,} | {stats['standard'][0]:.4f} ± {stats['standard'][1]:.4f} | {stats['radix'][0]:.4f} ± {stats['radix'][1]:.4f} | {faster} |")
    svg_chart(RESULTS / "s5_sort.svg", "S5 sorting by group", "Sort time (ms)", [("Standard mean ± SD", sort_series["standard"], "#16609e"), ("Radix mean ± SD", sort_series["radix"], "#e05a38")])
    lines += ["", "![S5 sorting comparison](s5_sort.svg)", "", "The full 100,000-row outputs are `s5_standard.csv` and `s5_radix.csv`. An independent CSV check confirmed that each has all source email identifiers exactly once and is ordered by `m_group`. Their within-group row order may differ, as the assignment permits.", "", "## Defense notes", "", "The ranked-set design is rational for the given 50:100:100 mix because two of the three frequent operations ask for maxima. Differential tests check all query answers after 1,000 random changes; the timed run also validates index consistency afterward. With untrusted inputs, both email and group hash tables can suffer collision attacks: use ordered maps for both to guarantee logarithmic lookups, keep balanced group rankings, validate input sizes, and paginate a potentially huge tie result. CSV parsing and operation generation happen before timing.", ""]
    (RESULTS / "REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
