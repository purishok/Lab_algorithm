"""Структури бази студентів V4 і сортування S5 за групою (лише стандартна бібліотека Python)."""

from __future__ import annotations

import csv
import heapq
import sys
from dataclasses import dataclass, fields
from fractions import Fraction
from operator import attrgetter
from pathlib import Path
from typing import Iterable


FIELD_NAMES = (
    "m_name", "m_surname", "m_email", "m_birth_year", "m_birth_month",
    "m_birth_day", "m_group", "m_rating", "m_phone_number",
)


@dataclass(slots=True)
class Student:
    m_name: str
    m_surname: str
    m_email: str
    m_birth_year: int
    m_birth_month: int
    m_birth_day: int
    m_group: str
    m_rating: float
    m_phone_number: str
    rating_cents: int

    def copy(self) -> Student:
        return Student(*(getattr(self, field.name) for field in fields(Student)))


def read_students(path: str | Path, limit: int = 100_000) -> list[Student]:
    students = []
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELD_NAMES:
            raise ValueError("Неочікуваний заголовок CSV")
        for row in reader:
            if len(students) == limit:
                break
            rating_text = row["m_rating"]
            whole, dot, decimal = rating_text.partition(".")
            if len(decimal) > 2 or (dot and not decimal):
                raise ValueError(f"Рейтинг має містити не більше двох десяткових знаків: {rating_text}")
            cents = int(whole) * 100 + int(decimal.ljust(2, "0") or "0")
            students.append(Student(
                row["m_name"], row["m_surname"], row["m_email"],
                int(row["m_birth_year"]), int(row["m_birth_month"]),
                int(row["m_birth_day"]), row["m_group"], float(rating_text),
                row["m_phone_number"], cents,
            ))
    return students


def write_students(path: str | Path, students: Iterable[Student]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELD_NAMES)
        for s in students:
            writer.writerow((
                s.m_name, s.m_surname, s.m_email, s.m_birth_year,
                s.m_birth_month, s.m_birth_day, s.m_group,
                f"{s.rating_cents // 100}.{s.rating_cents % 100:02d}", s.m_phone_number,
            ))


def _best_count(groups: dict[str, tuple[int, int]]) -> tuple[str, ...]:
    if not groups:
        return ()
    best = max(count for count, _ in groups.values())
    return tuple(group for group, (count, _) in groups.items() if count == best)


def _best_average(groups: dict[str, tuple[int, int]]) -> tuple[str, ...]:
    if not groups:
        return ()
    best = max(Fraction(total, count) for count, total in groups.values())
    return tuple(group for group, (count, total) in groups.items()
                 if Fraction(total, count) == best)


class VectorScan:
    """Реалізація А: список студентів; кожна операція переглядає записи."""

    def __init__(self, source: list[Student]):
        self.students = [s.copy() for s in source]

    def _groups(self) -> dict[str, tuple[int, int]]:
        groups: dict[str, tuple[int, int]] = {}
        for s in self.students:
            count, total = groups.get(s.m_group, (0, 0))
            groups[s.m_group] = (count + 1, total + s.rating_cents)
        return groups

    def largest_groups(self) -> tuple[str, ...]:
        return _best_count(self._groups())

    def highest_average_groups(self) -> tuple[str, ...]:
        return _best_average(self._groups())

    def change_group(self, email: str, new_group: str) -> bool:
        for s in self.students:
            if s.m_email == email:
                s.m_group = new_group
                return True
        return False

    def validate(self) -> bool:
        return True


class AggregateMap:
    """Реалізація Б: пошук за поштою та агрегати; запити максимуму переглядають групи."""

    def __init__(self, source: list[Student]):
        self.students = [s.copy() for s in source]
        self.by_email = {s.m_email: s for s in self.students}
        if len(self.by_email) != len(self.students):
            raise ValueError("Повторна адреса електронної пошти")
        self.groups: dict[str, tuple[int, int]] = {}
        for s in self.students:
            count, total = self.groups.get(s.m_group, (0, 0))
            self.groups[s.m_group] = (count + 1, total + s.rating_cents)

    def largest_groups(self) -> tuple[str, ...]:
        return _best_count(self.groups)

    def highest_average_groups(self) -> tuple[str, ...]:
        return _best_average(self.groups)

    def change_group(self, email: str, new_group: str) -> bool:
        s = self.by_email.get(email)
        if s is None:
            return False
        if s.m_group == new_group:
            return True
        count, total = self.groups[s.m_group]
        if count == 1:
            del self.groups[s.m_group]
        else:
            self.groups[s.m_group] = (count - 1, total - s.rating_cents)
        count, total = self.groups.get(new_group, (0, 0))
        self.groups[new_group] = (count + 1, total + s.rating_cents)
        s.m_group = new_group
        return True

    def validate(self) -> bool:
        expected: dict[str, tuple[int, int]] = {}
        for s in self.students:
            count, total = expected.get(s.m_group, (0, 0))
            expected[s.m_group] = (count + 1, total + s.rating_cents)
            if self.by_email.get(s.m_email) is not s:
                return False
        return expected == self.groups


class RankedIndex(AggregateMap):
    """Реалізація В: хешовані агрегати, обмежені купи максимумів і множини рівних максимумів."""

    def __init__(self, source: list[Student]):
        super().__init__(source)
        self.count_members: dict[int, set[str]] = {}
        self.average_members: dict[Fraction, set[str]] = {}
        for group, (count, total) in self.groups.items():
            self.count_members.setdefault(count, set()).add(group)
            self.average_members.setdefault(Fraction(total, count), set()).add(group)
        self.count_heap = [-key for key in self.count_members]
        self.average_heap = [-key for key in self.average_members]
        heapq.heapify(self.count_heap)
        heapq.heapify(self.average_heap)

    @staticmethod
    def _remove(members: dict, key: object, group: str) -> None:
        names = members[key]
        names.remove(group)
        if not names:
            del members[key]

    @staticmethod
    def _add(members: dict, heap: list, key: object, group: str) -> None:
        if key not in members:
            members[key] = set()
            heapq.heappush(heap, -key)
        members[key].add(group)

    @staticmethod
    def _top(members: dict, heap: list) -> tuple[str, ...]:
        while heap and -heap[0] not in members:
            heapq.heappop(heap)
        return tuple(members[-heap[0]]) if heap else ()

    def _unrank(self, group: str, count: int, total: int) -> None:
        self._remove(self.count_members, count, group)
        self._remove(self.average_members, Fraction(total, count), group)

    def _rank(self, group: str, count: int, total: int) -> None:
        self._add(self.count_members, self.count_heap, count, group)
        self._add(self.average_members, self.average_heap, Fraction(total, count), group)

    def _compact(self) -> None:
        # Перебудова обмежує кількість застарілих записів після тривалих оновлень.
        if len(self.count_heap) > 4 * len(self.count_members) + 1024:
            self.count_heap = [-key for key in self.count_members]
            heapq.heapify(self.count_heap)
        if len(self.average_heap) > 4 * len(self.average_members) + 1024:
            self.average_heap = [-key for key in self.average_members]
            heapq.heapify(self.average_heap)

    def largest_groups(self) -> tuple[str, ...]:
        return self._top(self.count_members, self.count_heap)

    def highest_average_groups(self) -> tuple[str, ...]:
        return self._top(self.average_members, self.average_heap)

    def change_group(self, email: str, new_group: str) -> bool:
        s = self.by_email.get(email)
        if s is None:
            return False
        if s.m_group == new_group:
            return True
        old_group = s.m_group
        old_count, old_total = self.groups[old_group]
        self._unrank(old_group, old_count, old_total)
        if old_count == 1:
            del self.groups[old_group]
        else:
            self.groups[old_group] = (old_count - 1, old_total - s.rating_cents)
            self._rank(old_group, *self.groups[old_group])
        if new_group in self.groups:
            self._unrank(new_group, *self.groups[new_group])
        new_count, new_total = self.groups.get(new_group, (0, 0))
        self.groups[new_group] = (new_count + 1, new_total + s.rating_cents)
        self._rank(new_group, *self.groups[new_group])
        s.m_group = new_group
        self._compact()
        return True

    def validate(self) -> bool:
        if not super().validate():
            return False
        expected_counts: dict[int, set[str]] = {}
        expected_averages: dict[Fraction, set[str]] = {}
        for group, (count, total) in self.groups.items():
            expected_counts.setdefault(count, set()).add(group)
            expected_averages.setdefault(Fraction(total, count), set()).add(group)
        return expected_counts == self.count_members and expected_averages == self.average_members


APPROACHES = {
    "vector_scan": VectorScan,
    "aggregate_map": AggregateMap,
    "ranked_index": RankedIndex,
}


def standard_group_sort(students: list[Student]) -> list[Student]:
    return sorted(students, key=attrgetter("m_group"))


def radix_group_sort(students: list[Student]) -> list[Student]:
    """Розподілити записи за групами, порозрядно впорядкувати ключі й об’єднати списки."""
    buckets: dict[str, list[Student]] = {}
    for s in students:
        buckets.setdefault(s.m_group, []).append(s)
    order = list(buckets)
    for group in order:
        if (len(group) != 6 or group[3] != "-" or
                any(not "A" <= character <= "Z" for character in group[:3]) or
                any(not "0" <= character <= "9" for character in group[4:])):
            raise ValueError(f"Неправильний формат групи S5: {group}")
    for position in (5, 4, 2, 1, 0):
        counts = [0] * 256
        for group in order:
            counts[ord(group[position])] += 1
        total = 0
        for i, count in enumerate(counts):
            counts[i], total = total, total + count
        next_order = [""] * len(order)
        for group in order:
            code = ord(group[position])
            next_order[counts[code]] = group
            counts[code] += 1
        order = next_order
    result: list[Student] = []
    for group in order:
        result.extend(buckets[group])
    return result


def deep_sizeof(root: object) -> int:
    """Оцінити розміри досяжних об’єктів Python, враховуючи кожний один раз."""
    seen: set[int] = set()

    def visit(obj: object) -> int:
        identity = id(obj)
        if identity in seen:
            return 0
        seen.add(identity)
        size = sys.getsizeof(obj)
        if isinstance(obj, dict):
            return size + sum(visit(key) + visit(value) for key, value in obj.items())
        if isinstance(obj, (list, tuple, set)):
            return size + sum(visit(value) for value in obj)
        if isinstance(obj, Student):
            return size + sum(visit(getattr(obj, field.name)) for field in fields(Student))
        if isinstance(obj, Fraction):
            return size + visit(obj.numerator) + visit(obj.denominator)
        if isinstance(obj, RankedIndex):
            return size + sum(visit(getattr(obj, name)) for name in
                              ("students", "by_email", "groups", "count_members", "average_members", "count_heap", "average_heap"))
        if isinstance(obj, AggregateMap):
            return size + visit(obj.students) + visit(obj.by_email) + visit(obj.groups)
        if isinstance(obj, VectorScan):
            return size + visit(obj.students)
        return size

    return visit(root)
