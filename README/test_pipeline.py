"""
End-to-End Validation & Reconciliation Test Suite
Verifies primary key uniqueness, foreign key joins, and ground truth recall.
"""

import csv
import unittest
from generate_data import generate_dataset
from detector import run_evaluation

class TestCompensationPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generate_dataset(scale=1000, output_dir="./test_data")
        cls.detected = run_evaluation(data_dir="./test_data")

    def test_pk_uniqueness(self):
        with open("./test_data/employees.csv") as f:
            ids = [r["employee_id"] for r in csv.DictReader(f)]
            self.assertEqual(len(ids), len(set(ids)), "Employee PK must be strictly unique.")

    def test_fk_integrity(self):
        with open("./test_data/employees.csv") as f:
            emp_ids = {r["employee_id"] for r in csv.DictReader(f)}
        with open("./test_data/salary_records.csv") as f:
            for r in csv.DictReader(f):
                self.assertIn(r["employee_id"], emp_ids, "Salary record references non-existent employee.")

    def test_ground_truth_reconciliation(self):
        with open("./test_data/ground_truth.csv") as f:
            ground_truth = list(csv.DictReader(f))

        detected_set = {(d["salary_record_id"], d["detected_issue"]) for d in self.detected}
        gt_set = {(g["salary_record_id"], g["issue_type"]) for g in ground_truth}

        tp = len(detected_set.intersection(gt_set))
        recall = tp / len(gt_set) if gt_set else 1.0
        self.assertGreaterEqual(recall, 0.90, f"Anomaly detection recall {recall:.2f} is below 0.90 threshold.")

if __name__ == "__main__":
    unittest.main()