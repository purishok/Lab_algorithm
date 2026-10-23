"""Підсумувати вимірювання Python, побудувати регресію найповільнішої операції V4 і графіки SVG."""

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
            raise ValueError("Матриця регресії вироджена")
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
        return [1.0, height, math.log2(n)]
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
    parts.append(f'<text x="{width/2}" y="{height-18}" text-anchor="middle" font-size="14" font-family="sans-serif">Кількість студентів (логарифмічна шкала)</text>')
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
        parts.append(f'<rect x="{left+index*330}" y="{height-42}" width="16" height="4" fill="{color}"/>')
        parts.append(f'<text x="{left+index*330+22}" y="{height-35}" font-size="12" font-family="sans-serif">{label}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    compared = read_csv(RESULTS / "v4_comparison.csv")
    if {row["approach"] for row in compared} != {"vector_scan", "aggregate_map", "ranked_index"}:
        raise ValueError("Очікуються всі три реалізації V4 на Python")
    winner = max(compared, key=lambda row: int(row["operations"]) / float(row["elapsed_s"]))["approach"]
    benchmark = read_csv(RESULTS / "v4_benchmark.csv")
    by_size: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in benchmark:
        if row["approach"] != winner:
            raise ValueError("Дані для десяти обсягів не відповідають переможцю порівняння")
        by_size[int(row["n"])].append(row)
    if len(by_size) != 10 or any(len(rows) < 5 for rows in by_size.values()):
        raise ValueError("Очікуються десять обсягів із п’ятьма запусками для кожного")
    students = read_csv(Path("students.csv"))
    summary = []
    for n, rows in sorted(by_size.items()):
        group_counts = Counter(student["m_group"] for student in students[:n])
        operations = [int(row["operations"]) * 10 / float(row["elapsed_s"]) for row in rows]
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
    svg_chart(RESULTS / "slowest_regression.svg", f"Операція {regression_operation + 1} V4 на Python та регресія", "Середній час операції (нс)",
              [("Вимірювання ± станд. відх.", actual, "#16609e"), ("Метод найменших квадратів", predicted, "#e05a38")])
    svg_chart(RESULTS / "throughput.svg", "Продуктивність змішаного навантаження V4 на Python", "Кількість операцій за 10 секунд",
              [("Середнє ± станд. відх.", [(row["n"], row["throughput"], row["throughput_sd"]) for row in summary], "#16885b")])

    lines = ["# Звіт про вимірювання V4 та S5 на Python", "",
             "Призначений варіант: V4, співвідношення операцій 50:100:100, S5 — сортування за групою. Використано стандартну бібліотеку Python.", "",
             f"Середовище: Python {platform.python_version()}, {platform.system()} {platform.machine()}.", "",
             "## Завдання I: три реалізації для 100 000 студентів", "",
             "Усі реалізації отримують однакову заздалегідь підготовлену послідовність із 25 000 операцій. Кожний перемішаний блок із 250 операцій містить рівно 50, 100 і 100 операцій типів 1, 2 та 3. Поштові адреси й цільові групи наявні у вхідних даних. У першій половині виконуються випадкові перенесення до іншої групи, у другій — їх скасування у зворотному порядку, перемежовані випадково впорядкованими запитами. Кожне перенесення змінює групу, а повний цикл відновлює початкову базу, тому повторення циклу зберігає реальні зміни. Це оборотне навантаження, а не потік незалежних оновлень. Підготовку й перевірку виключено з вимірювань. Останні блоки можуть трохи збільшити тривалість понад 10 секунд; нормована продуктивність це враховує.", "",
             "| Реалізація | Структури даних | Виконано операцій | Час, с | Операцій за 10 с |",
             "|---|---|---:|---:|---:|"]
    descriptions = {
        "vector_scan": "список, тимчасовий словник груп",
        "aggregate_map": "словник пошти, словник агрегатів груп",
        "ranked_index": "словники пошти й груп, множини рівних максимумів, обмежені купи максимумів",
    }
    for row in compared:
        elapsed = float(row["elapsed_s"])
        operations = int(row["operations"])
        lines.append(f"| {row['approach']} | {descriptions[row['approach']]} | {operations:,} | {elapsed:.3f} | {operations * 10 / elapsed:,.0f} |")
    lines += ["", f"**Переможець: `{winner}`.** Перегляд списку потребує O(n) для кожної операції. Словник агрегатів змінює групу за очікуваний час O(1), а для запитів максимуму переглядає g груп. Індекс максимумів використовує словники, точні середні у вигляді `Fraction`, множини рівних максимумів та обмежені купи з відкладеним видаленням; оновлення мають очікувану амортизовану вартість O(log g), а повернення k груп-переможців — амортизовану O(k). Запити максимуму становлять 60% навантаження.", "",
              "## Переможець для десяти обсягів бази", "", "СВ — стандартне відхилення між повтореннями.", "",
              "Для кожного обсягу виконано п’ять незалежних запусків по 10 секунд. Послідовність операцій готується перед кожним запуском і повторюється циклічно. Початкову побудову бази та кінцеву перевірку виключено з вимірювань. Час операцій вимірюється кожні 128 виконань кожного типу; таймер і планування процесів додають шум.", "",
              f"| Студентів | Груп | Частка студентів у групах з одним учасником | Операцій за 10 с, середнє ± СВ | Оп. 1, нс, середнє ± СВ | Оп. 2, нс, середнє ± СВ | Оп. 3, нс, середнє ± СВ | Найповільніша при n | Прогноз оп. {regression_operation + 1}, нс | Оцінка пам’яті, байтів |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row, (_, prediction, _) in zip(summary, predicted):
        latency = " | ".join(f"{mean:.1f} ± {deviation:.1f}" for mean, deviation in zip(row["means"], row["deviations"]))
        lines.append(f"| {row['n']:,} | {row['groups']:,} | {row['singleton_share']:.1%} | {row['throughput']:,.0f} ± {row['throughput_sd']:,.0f} | {latency} | {row['slowest'] + 1} | {prediction:.1f} | {row['memory']:,} |")
    if winner == "ranked_index":
        formula = (f"T(n) = {coefficients[0]:.4f} + {coefficients[1]:.4f} log₂(g(n)) + "
                   f"{coefficients[2]:.4f} log₂(n) нс")
        basis_note = "Базисні функції: f1(n)=1, f2(n)=log₂(g(n)) та f3(n)=log₂(n). Вони описують очікувану сталу вартість роботи зі словниками й множинами, амортизоване обслуговування куп і нормалізацію точного середнього: Fraction скорочує цілі суми рейтингів і кількості через НСД. Алгоритм Евкліда потребує O(log n) арифметичних кроків, оскільки рейтинги обмежені, а суми й кількості мають порядок O(n). Модель розділяє структурні операції та нормалізацію цілих чисел; це пояснювальна модель витрат, а не повна оцінка бітової складності. Тут g(n) — початкова кількість груп і верхня межа під час перенесень; порожні групи можуть тимчасово зникати."
    elif winner == "aggregate_map":
        formula = f"T(n) = {coefficients[0]:.4f} + {coefficients[1]:.4f} g(n) + {coefficients[2]:.4f} g(n)/n нс"
        basis_note = "Доданки описують сталі витрати, перегляд g груп та вплив заповненості; останній доданок є евристичним."
    else:
        formula = f"T(n) = {coefficients[0]:.4f} + {coefficients[1]:.4f} n + {coefficients[2]:.4f} g(n) нс"
        basis_note = "Доданки описують сталі витрати, перегляд n студентів і побудову та перегляд агрегатів g груп."
    lines += ["", "## Регресія та пам’ять", "",
              f"Нехай g(n) — кількість різних груп у перших n вхідних записах, наведена в таблиці. Операція {regression_operation + 1} має найбільший середній час серед десяти обсягів. {formula}; R² = {r_squared:.4f}.", "",
              basis_note + f" Коефіцієнти отримано методом найменших квадратів за десятьма середніми значеннями часу операції {regression_operation + 1}. У таблиці також зазначено найповільнішу операцію для кожного обсягу. Модель не слід екстраполювати за межі дослідженого діапазону. Вона описує конкретний набір даних і не доводить асимптотичного зростання. Кількість різних груп наближається до 4 000, тому вартість оновлень не обов’язково зростає монотонно з n.", "",
              "Пам’ять оцінено через `deep_sizeof(database)` перед вимірюванням: `sys.getsizeof` підсумовує розміри досяжних списків, словників, множин, кортежів, елементів куп, об’єктів студентів, рядків, цілих чисел і дробів, враховуючи кожний об’єкт один раз. Незмінні рядки, спільні з вхідними об’єктами, включено, оскільки база посилається на них. Окремий вхідний список, інтерпретатор Python, накладні витрати розподілювача пам’яті, вхідний CSV та підготовлену послідовність операцій виключено; це не резидентна пам’ять процесу (RSS).", "",
              "![Найповільніша операція та регресія](slowest_regression.svg)", "",
              "![Продуктивність змішаного навантаження](throughput.svg)", "",
              "## Завдання II: сортування S5 за групою", "",
              "`standard` використовує `sorted` із ключем групи, O(n log n). `radix` створює словник списків за групами, впорядковує різні ключі формату `AAA-00` п’ятьма стабільними проходами сортування підрахунком і об’єднує списки: O(n + 5(g + 256)). Вимірювання охоплює створення всіх допоміжних структур і виключає запис CSV. Для кожного обсягу та методу виконано п’ять повторень; порядок методів чергується.", "",
              "| Студентів | Стандартне, мс, середнє ± СВ | Порозрядне, мс, середнє ± СВ | Швидший метод |",
              "|---:|---:|---:|---|"]
    sorting = read_csv(RESULTS / "s5_benchmark.csv")
    sort_series = {"standard": [], "radix": []}
    for n in sorted(by_size):
        stats = {}
        for method in ("standard", "radix"):
            values = [float(row["sort_ms"]) for row in sorting if int(row["n"]) == n and row["method"] == method]
            if len(values) != 5:
                raise ValueError(f"Очікуються п’ять запусків сортування для n={n}/{method}")
            stats[method] = (statistics.mean(values), statistics.stdev(values))
            sort_series[method].append((n, *stats[method]))
        faster = min(stats, key=lambda method: stats[method][0])
        lines.append(f"| {n:,} | {stats['standard'][0]:.4f} ± {stats['standard'][1]:.4f} | {stats['radix'][0]:.4f} ± {stats['radix'][1]:.4f} | { {'standard': 'Стандартне', 'radix': 'Порозрядне'}[faster]} |")
    svg_chart(RESULTS / "s5_sort.svg", "Сортування S5 за групою на Python", "Час сортування (мс)",
              [("Стандартне: середнє ± СВ", sort_series["standard"], "#16609e"),
               ("Порозрядне: середнє ± СВ", sort_series["radix"], "#e05a38")])
    lines += ["", "![Порівняння сортувань S5](s5_sort.svg)", "",
              "Повні відсортовані результати: `s5_standard.csv` та `s5_radix.csv`. Незалежні перевірки підтверджують зростання груп і точне збереження всіх вхідних полів та поштових ідентифікаторів; порядок записів з однаковою групою не визначено.", "",
              "## Примітки до захисту", "",
              "Усі три реалізації проходять диференційні тести після випадкових змін груп, зокрема для рівних максимумів і зникнення груп. Індекс максимумів періодично перебудовує купи із застарілими ключами, обмежуючи пам’ять. Словники Python використовують рандомізоване хешування рядків, але не гарантують детермінованого найгіршого часу пошуку. Для зловмисно підібраних даних можна замінити словники пошти та груп збалансованими деревами з пошуком O(log n), перевіряти розміри й формати та розбивати великі відповіді з рівними максимумами на сторінки.", ""]
    (RESULTS / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
