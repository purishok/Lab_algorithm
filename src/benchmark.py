"""Відтворювані експерименти зі змішаним навантаженням V4 та сортуванням S5."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path
from time import perf_counter_ns

from .lab import (
    APPROACHES, Student, deep_sizeof, radix_group_sort, read_students,
    standard_group_sort, write_students,
)


SIZES = (100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000)


def operation_tape(source: list[Student], seed: int) -> list[tuple[int, str, str]]:
    rng = random.Random(seed)
    emails = [s.m_email for s in source]
    groups = sorted({s.m_group for s in source})
    if len(groups) < 2:
        raise ValueError("Для навантаження зі зміною груп потрібні щонайменше дві вхідні групи")
    current = {s.m_email: s.m_group for s in source}
    undo = []
    tape = []
    for block_number in range(100):
        kinds = [1] * 50 + [2] * 100 + [3] * 100
        rng.shuffle(kinds)
        for kind in kinds:
            email = group = ""
            if kind == 2:
                if block_number < 50:
                    email = rng.choice(emails)
                    old_group = current[email]
                    group = rng.choice(groups)
                    while group == old_group:
                        group = rng.choice(groups)
                    undo.append((email, old_group))
                else:
                    email, group = undo.pop()
                current[email] = group
            tape.append((kind, email, group))
    # Зворотні перенесення відновлюють початковий стан, тому кожний цикл
    # зберігає реальні зміни. Підготовку виключено з вимірювання часу.
    assert current == {s.m_email: s.m_group for s in source}
    return tape


def run_workload(database, tape, seconds: float, sample: bool):
    query_count = database.largest_groups
    change_group = database.change_group
    query_average = database.highest_average_groups
    counts = [0, 0, 0]
    samples = [0, 0, 0]
    sampled_ns = [0, 0, 0]
    checksum = 0
    position = 0
    start = perf_counter_ns()
    deadline = start + int(seconds * 1_000_000_000)
    while True:
        for _ in range(32):
            kind, email, group = tape[position]
            position += 1
            if position == len(tape):
                position = 0
            index = kind - 1
            measured = sample and counts[index] % 128 == 0
            if measured:
                before = perf_counter_ns()
            if kind == 1:
                checksum += len(query_count())
            elif kind == 2:
                checksum += change_group(email, group)
            else:
                checksum += len(query_average())
            if measured:
                sampled_ns[index] += perf_counter_ns() - before
                samples[index] += 1
            counts[index] += 1
        if perf_counter_ns() >= deadline:
            break
    elapsed = (perf_counter_ns() - start) / 1_000_000_000
    if not database.validate():
        raise AssertionError("База даних не пройшла перевірку після запуску")
    means = [sampled_ns[k] / samples[k] if samples[k] else 0 for k in range(3)]
    return elapsed, counts, means, checksum


def compare(all_students: list[Student], output: Path, seconds: float) -> None:
    tape = operation_tape(all_students, 20261016)
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("approach", "elapsed_s", "operations", "op1_count", "op2_count", "op3_count", "checksum"))
        for name, factory in APPROACHES.items():
            database = factory(all_students)
            elapsed, counts, _, checksum = run_workload(database, tape, seconds, False)
            writer.writerow((name, f"{elapsed:.6f}", sum(counts), *counts, checksum))
            stream.flush()
            print(f"{name}: {sum(counts):,} операцій за {elapsed:.3f} с", file=sys.stderr)


def benchmark_winner(all_students: list[Student], comparison: Path, output: Path,
                     seconds: float, repetitions: int) -> None:
    with comparison.open(newline="") as stream:
        compared = list(csv.DictReader(stream))
    if {row["approach"] for row in compared} != set(APPROACHES):
        raise ValueError("Спочатку порівняйте всі три реалізації")
    winner = max(compared, key=lambda row: int(row["operations"]) / float(row["elapsed_s"]))["approach"]
    print(f"Переможець: {winner}", file=sys.stderr)
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("approach", "n", "rep", "operations", "op1_count", "op2_count", "op3_count",
                         "op1_mean_ns", "op2_mean_ns", "op3_mean_ns", "estimated_bytes", "elapsed_s", "checksum"))
        for n in SIZES:
            source = all_students[:n]
            for rep in range(1, repetitions + 1):
                database = APPROACHES[winner](source)
                tape = operation_tape(source, 20261016 + n * 31 + rep)
                memory = deep_sizeof(database)
                elapsed, counts, means, checksum = run_workload(database, tape, seconds, True)
                writer.writerow((winner, n, rep, sum(counts), *counts,
                                 *(f"{mean:.3f}" for mean in means), memory, f"{elapsed:.6f}", checksum))
                stream.flush()
                print(f"n={n}, повторення={rep}, операцій={sum(counts):,}", file=sys.stderr)


def benchmark_sort(all_students: list[Student], output: Path,
                   standard_output: Path, radix_output: Path) -> None:
    methods = {"standard": standard_group_sort, "radix": radix_group_sort}
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("n", "rep", "method", "sort_ms"))
        for n in SIZES:
            source = all_students[:n]
            for rep in range(1, 6):
                order = ("standard", "radix") if rep % 2 else ("radix", "standard")
                for name in order:
                    start = perf_counter_ns()
                    result = methods[name](source)
                    elapsed_ms = (perf_counter_ns() - start) / 1_000_000
                    if any(a.m_group > b.m_group for a, b in zip(result, result[1:])):
                        raise AssertionError(f"Сортування S5 {name} не пройшло перевірку порядку")
                    writer.writerow((n, rep, name, f"{elapsed_ms:.6f}"))
            stream.flush()
            print(f"S5 n={n}: завершено", file=sys.stderr)
    write_students(standard_output, standard_group_sort(all_students))
    write_students(radix_output, radix_group_sort(all_students))


def demo(all_students: list[Student]) -> None:
    database = APPROACHES["ranked_index"](all_students)
    print("Команди: кількість | перенести ПОШТА ГРУПА | середнє | вихід")
    while True:
        try:
            parts = input("> ").split()
        except EOFError:
            break
        if parts in (["вихід"], ["quit"]):
            break
        if parts in (["кількість"], ["count"]):
            print(", ".join(sorted(database.largest_groups())))
        elif parts in (["середнє"], ["average"]):
            print(", ".join(sorted(database.highest_average_groups())))
        elif len(parts) == 3 and parts[0] in ("перенести", "move"):
            print("Групу змінено" if database.change_group(parts[1], parts[2]) else "Адресу електронної пошти не знайдено")
        else:
            print("Команди: кількість | перенести ПОШТА ГРУПА | середнє | вихід")
    if not database.validate():
        raise AssertionError("База даних не пройшла перевірку узгодженості")


class UkrainianArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        return super().format_help().replace("usage:", "Використання:", 1)

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "Використання:", 1)

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        if message != "Тривалість і кількість повторень мають бути додатними":
            message = "Неправильні аргументи командного рядка. Перегляньте довідку --help."
        self.exit(2, f"{self.prog}: помилка: {message}\n")


def main() -> None:
    parser = UkrainianArgumentParser(
        description=__doc__, add_help=False,
        usage="%(prog)s КОМАНДА [--input ФАЙЛ] [--results КАТАЛОГ] [--seconds СЕКУНДИ] [--repetitions КІЛЬКІСТЬ]",
    )
    parser._positionals.title = "Позиційні аргументи"
    parser._optionals.title = "Параметри"
    parser.add_argument("-h", "--help", action="help", help="Показати довідку та завершити роботу")
    parser.add_argument("command", choices=("compare", "winner", "sort", "demo"), help="compare — порівняння; winner — вимірювання переможця; sort — сортування; demo — демонстрація")
    parser.add_argument("--input", default="students.csv", metavar="ФАЙЛ", help="Вхідний файл CSV")
    parser.add_argument("--results", default="results", metavar="КАТАЛОГ", help="Каталог результатів")
    parser.add_argument("--seconds", type=float, default=10, metavar="СЕКУНДИ", help="Тривалість одного запуску в секундах")
    parser.add_argument("--repetitions", type=int, default=5, metavar="КІЛЬКІСТЬ", help="Кількість повторень")
    args = parser.parse_args()
    if args.seconds <= 0 or args.repetitions <= 0:
        parser.error("Тривалість і кількість повторень мають бути додатними")
    all_students = read_students(args.input)
    if len(all_students) != 100_000:
        raise ValueError("Очікуються всі 100 000 вхідних записів студентів")
    results = Path(args.results)
    results.mkdir(parents=True, exist_ok=True)
    if args.command == "compare":
        compare(all_students, results / "v4_comparison.csv", args.seconds)
    elif args.command == "winner":
        benchmark_winner(all_students, results / "v4_comparison.csv",
                         results / "v4_benchmark.csv", args.seconds, args.repetitions)
    elif args.command == "sort":
        benchmark_sort(all_students, results / "s5_benchmark.csv",
                       results / "s5_standard.csv", results / "s5_radix.csv")
    else:
        demo(all_students)


if __name__ == "__main__":
    main()
