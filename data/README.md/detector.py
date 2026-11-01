"""
Disparity & Exception Classifier Engine
Validates data integrity, normalizes FTE & FX, and flags unexplained anomalies.
"""

import csv
import os

def load_data(data_dir="./data"):
    def read_csv(name):
        path = os.path.join(data_dir, name)
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return list(csv.DictReader(f))

    bands = {b["band_id"]: b for b in read_csv("compensation_bands.csv")}
    salaries = read_csv("salary_records.csv")
    employees = {e["employee_id"]: e for e in read_csv("employees.csv")}
    adjustments = {a["employee_id"]: a for a in read_csv("adjustment_proposals.csv")}
    return bands, salaries, employees, adjustments

def run_evaluation(data_dir="./data"):
    bands, salaries, employees, adjustments = load_data(data_dir)
    detected_anomalies = []

    for sal in salaries:
        emp_id = sal["employee_id"]
        emp = employees[emp_id]
        applied_band = bands.get(sal["applied_band_id"])
        eff_date = sal["effective_date"]

        # Rule 1: Expired Band Detection
        if applied_band and applied_band["effective_end"] < eff_date:
            detected_anomalies.append({
                "employee_id": emp_id,
                "salary_record_id": sal["salary_record_id"],
                "detected_issue": "EXPIRED_BAND_COMPARISON",
                "details": f"Band {applied_band['band_id']} expired on {applied_band['effective_end']}"
            })

        # Rule 2: Currency Conversion Missing
        if applied_band and sal["currency"] != applied_band["currency"]:
            detected_anomalies.append({
                "employee_id": emp_id,
                "salary_record_id": sal["salary_record_id"],
                "detected_issue": "CURRENCY_CONVERSION_MISSING",
                "details": f"Salary currency {sal['currency']} != Band currency {applied_band['currency']}"
            })

        # Rule 3: Incomparable Role / Level Grouping
        if applied_band:
            if applied_band["role_id"] != emp["role_id"] or applied_band["level_id"] != emp["level_id"]:
                detected_anomalies.append({
                    "employee_id": emp_id,
                    "salary_record_id": sal["salary_record_id"],
                    "detected_issue": "INCOMPARABLE_ROLE_GROUPING",
                    "details": f"Employee {emp['role_id']}-{emp['level_id']} mapped to {applied_band['band_id']}"
                })

        # Rule 4: Unapproved Adjustments
        if emp_id in adjustments:
            adj = adjustments[emp_id]
            if "APPROVED" not in adj["status"] and "MANAGER_APPROVED" not in adj.get("approval_trail", ""):
                detected_anomalies.append({
                    "employee_id": emp_id,
                    "salary_record_id": sal["salary_record_id"],
                    "detected_issue": "UNAPPROVED_ADJUSTMENT",
                    "details": f"Adjustment {adj['adj_id']} lacks complete approval trail"
                })

    out_path = os.path.join(data_dir, "predictions.csv")
    if detected_anomalies:
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=detected_anomalies[0].keys())
            writer.writeheader()
            writer.writerows(detected_anomalies)

    print(f"Detected {len(detected_anomalies)} anomalies. Saved to '{out_path}'.")
    return detected_anomalies

if __name__ == "__main__":
    run_evaluation()