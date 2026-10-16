import random
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from fractions import Fraction

from src.lab import (
    APPROACHES,
    Student,
    deep_sizeof,
    radix_group_sort,
    read_students,
    standard_group_sort,
    write_students,
)


def expected(rows):
    groups = defaultdict(lambda: [0, 0])
    for s in rows:
        groups[s.m_group][0] += 1
        groups[s.m_group][1] += s.rating_cents
    if not groups:
        return set(), set()
    maximum = max(count for count, _ in groups.values())
    average_group = max(groups, key=lambda group: Fraction(groups[group][1], groups[group][0]))
    best_total, best_count = groups[average_group][1], groups[average_group][0]
    return (
        {group for group, (count, _) in groups.items() if count == maximum},
        {group for group, (count, total) in groups.items()
         if total * best_count == best_total * count},
    )


class HomeworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all_students = read_students("students.csv")

    def test_all_v4_approaches_after_mutations(self):
        rows = [s.copy() for s in self.all_students[:1000]]
        databases = [factory(rows) for factory in APPROACHES.values()]
        rng = random.Random(442)
        for step in range(1000):
            index = rng.randrange(len(rows))
            group = "NEW-01" if step % 7 == 0 else f"GAA-{rng.randrange(30):02d}"
            email = rows[index].m_email
            for db in databases:
                self.assertTrue(db.change_group(email, group))
            rows[index].m_group = group
            if step % 20 == 0:
                count, average = expected(rows)
                for db in databases:
                    self.assertEqual(set(db.largest_groups()), count)
                    self.assertEqual(set(db.highest_average_groups()), average)
                    self.assertTrue(db.validate())
        for db in databases:
            self.assertFalse(db.change_group("missing@student.org", "NEW-01"))
            self.assertTrue(db.validate())

    def test_empty_and_ties(self):
        for factory in APPROACHES.values():
            empty = factory([])
            self.assertEqual(empty.largest_groups(), ())
            self.assertEqual(empty.highest_average_groups(), ())
            source = [
                Student("A", "A", "a", 2000, 1, 1, "AAA-01", 1.0, "p1", 100),
                Student("B", "B", "b", 2000, 1, 1, "BBB-01", 2.0, "p2", 200),
                Student("C", "C", "c", 2000, 1, 1, "BBB-01", 0.0, "p3", 0),
                Student("D", "D", "d", 2000, 1, 1, "AAA-01", 1.0, "p4", 100),
            ]
            db = factory(source)
            self.assertEqual(set(db.largest_groups()), {"AAA-01", "BBB-01"})
            self.assertEqual(set(db.highest_average_groups()), {"AAA-01", "BBB-01"})
            self.assertTrue(db.change_group("b", "AAA-01"))
            self.assertTrue(db.change_group("c", "CCC-01"))
            self.assertTrue(db.validate())
            self.assertEqual(set(db.largest_groups()), {"AAA-01"})

    def test_full_dataset_and_memory(self):
        self.assertEqual(len(self.all_students), 100_000)
        index = APPROACHES["ranked_index"](self.all_students)
        self.assertTrue(index.validate())
        self.assertGreater(deep_sizeof(index), 0)
        count, average = expected(self.all_students)
        self.assertEqual(set(index.largest_groups()), count)
        self.assertEqual(set(index.highest_average_groups()), average)

    def test_ranked_heaps_stay_bounded(self):
        rows = [s.copy() for s in self.all_students[:100]]
        index = APPROACHES["ranked_index"](rows)
        rng = random.Random(93)
        groups = sorted({s.m_group for s in rows})
        for _ in range(5000):
            student = rng.choice(rows)
            self.assertTrue(index.change_group(student.m_email, rng.choice(groups)))
        self.assertTrue(index.validate())
        self.assertLessEqual(len(index.count_heap), 4 * len(index.count_members) + 1024)
        self.assertLessEqual(len(index.average_heap), 4 * len(index.average_members) + 1024)
        count, average = expected(index.students)
        self.assertEqual(set(index.largest_groups()), count)
        self.assertEqual(set(index.highest_average_groups()), average)

    def test_s5_sort_and_csv(self):
        standard = standard_group_sort(self.all_students)
        radix = radix_group_sort(self.all_students)
        self.assertEqual([s.m_group for s in standard], [s.m_group for s in radix])
        self.assertEqual(sorted(s.m_email for s in self.all_students), sorted(s.m_email for s in radix))
        self.assertEqual([s.m_group for s in radix], sorted(s.m_group for s in radix))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sorted.csv"
            write_students(path, radix)
            reread = read_students(path)
            self.assertEqual(len(reread), len(radix))
            for a, b in zip(reread, radix):
                self.assertEqual(a, b)

    def test_invalid_group_for_radix(self):
        row = self.all_students[0].copy()
        row.m_group = "ААА-01"
        with self.assertRaises(ValueError):
            radix_group_sort([row])


if __name__ == "__main__":
    unittest.main()
