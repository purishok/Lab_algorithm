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
    # n is scaled for numerical stability; convert its coefficient back below.
    features = [[1.0, math.log2(n), n / 100000.0] for n, value in points]
    y = [value for n, value in points]
    matrix = [[sum(row[i] * row[j] for row in features) for j in range(3)] for i in range(3)]
    vector = [sum(row[i] * value for row, value in zip(features, y)) for i in range(3)]
    c0, c_log, c_scaled = solve_3x3(matrix, vector)
    return c0, c_log, c_scaled / 100000.0


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
    coefficients = fit([(n, means[slowest - 1]) for n, _, _, means, _, slowest, *_ in summary])
    predicted = [(n, coefficients[0] + coefficients[1] * math.log2(n) + coefficients[2] * n, 0) for n, *_ in summary]
    actual = [(n, means[slowest - 1], stds[slowest - 1]) for n, _, _, means, stds, slowest, *_ in summary]
    fitted = {n: value for n, value, _ in predicted}
    observed = [value for _, value, _ in actual]
    total_error = sum((value - statistics.mean(observed)) ** 2 for value in observed)
    residual_error = sum((value - fitted[n]) ** 2 for n, value, _ in actual)
    r_squared = 1 - residual_error / total_error if total_error else float("nan")
    svg_chart(RESULTS / "slowest_regression.svg", "Slowest V4 operation and regression", "Mean latency (ns)", [("Measured ± SD", actual, "#16609e"), ("Least squares fit", predicted, "#e05a38")])
    svg_chart(RESULTS / "throughput.svg", "V4 mixed workload throughput", "Operations in 10 seconds", [("Mean ± SD", [(n, rate, sd) for n, rate, sd, *_ in summary], "#16885b")])
    c0, c_log, c_n = coefficients
    lines = ["# V4 benchmark results", "", "Variant: V4, ratio 50:100:100. Each row averages five independent 10 second runs. The operation tape contains 25,000 randomly shuffled, preselected operations and repeats cyclically. Student emails and destination groups are chosen from existing values before timing. The initial index build and the final validation are outside the timed interval.", "", "| Students | Groups | Singleton share | Operations / 10 s, mean ± SD | Op 1 ns, mean ± SD | Op 2 ns, mean ± SD | Op 3 ns, mean ± SD | Slowest | Predicted T(n), ns | Estimated bytes |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for n, rate, sd, means, stds, slowest, memory, group_count, singleton_fraction in summary:
        latency = " | ".join(f"{mean:.1f} ± {sd_value:.1f}" for mean, sd_value in zip(means, stds))
        lines.append(f"| {n:,} | {group_count:,} | {singleton_fraction:.1%} | {rate:,.0f} ± {sd:,.0f} | {latency} | {slowest} | {fitted[n]:.1f} | {memory:,} |")
    sign = "+" if c_n >= 0 else "−"
    lines += ["", "## Regression", "", f"T(n) = {c0:.4f} + {c_log:.4f} log₂(n) {sign} {abs(c_n):.9f} n nanoseconds; R² = {r_squared:.4f}.", "", "The basis reflects constant-time work, ordered-set updates with O(log g) complexity for g groups (bounded by n), and the O(n) worst case of the email hash lookup under collisions. It is fitted to the slowest mean operation at each database size. This is a weak descriptive fit: the linear coefficient is negative and the model predicts the 100,000-student case poorly. Group count saturates near 4,000 while the share of singleton groups falls to zero, changing the cost of updates that remove and recreate groups. The benchmark cannot establish an asymptotic growth law from these ten points. Latencies are sampled every 128 operations, so timer overhead and operating-system scheduling contribute to measured variance.", "", "## Memory method", "", "`estimated_bytes()` sums vector capacity, string capacities, hash buckets and approximate nodes, and ordered-set nodes. This is a reproducible approximation, not process RSS: allocator metadata, code, stack, the prepared operation tape, and source CSV are excluded. Short strings may be stored inline, so counting their capacities can overstate heap use.", "", "![Slowest operation and fit](slowest_regression.svg)", "", "![Throughput](throughput.svg)", ""]
    (RESULTS / "REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
