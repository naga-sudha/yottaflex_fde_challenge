"""
Deterministic Synthetic Data Generator
Generates master, event, and time-series data with zero-leak ground truth anomalies.
"""

import csv
import hashlib
import json
import os
import random
from datetime import date

FIXED_SEED = 20261022
NUM_EMPLOYEES = 5000

def set_seed(seed=FIXED_SEED):
    random.seed(seed)

def generate_dataset(scale=NUM_EMPLOYEES, output_dir="./data"):
    set_seed()
    os.makedirs(output_dir, exist_ok=True)

    roles = ["SWE", "DATA_ENG", "PRODUCT_MGR", "DESIGNER", "DEVOPS", "QA"]
    levels = ["L1", "L2", "L3", "L4", "L5"]
    locations = ["HYD", "SFO", "LON"]

    bands = []
    base_salaries = {
        "SWE": {"L1": 70000, "L2": 95000, "L3": 130000, "L4": 170000, "L5": 220000},
        "DATA_ENG": {"L1": 68000, "L2": 92000, "L3": 125000, "L4": 165000, "L5": 210000},
        "PRODUCT_MGR": {"L1": 75000, "L2": 105000, "L3": 140000, "L4": 180000, "L5": 230000},
        "DESIGNER": {"L1": 60000, "L2": 80000, "L3": 110000, "L4": 145000, "L5": 185000},
        "DEVOPS": {"L1": 70000, "L2": 95000, "L3": 130000, "L4": 168000, "L5": 215000},
        "QA": {"L1": 55000, "L2": 72000, "L3": 98000, "L4": 130000, "L5": 165000},
    }

    band_currencies = {"SFO": "USD", "LON": "GBP", "HYD": "INR"}
    band_multipliers = {"SFO": 1.0, "LON": 0.8, "HYD": 82.0}

    # Step 1 & 2: Generate Compensation Bands
    for yr in [2023, 2024, 2025]:
        start = f"{yr}-01-01"
        end = f"{yr}-12-31"
        for r in roles:
            for lvl in levels:
                for loc in locations:
                    curr = band_currencies[loc]
                    raw_mid = base_salaries[r][lvl] * band_multipliers[loc] * (1 + (yr - 2023) * 0.05)
                    min_val = round(raw_mid * 0.8, -2)
                    mid_val = round(raw_mid, -2)
                    max_val = round(raw_mid * 1.2, -2)
                    bands.append({
                        "band_id": f"BAND-{r}-{lvl}-{loc}-{yr}",
                        "role_id": r, "level_id": lvl, "location_id": loc,
                        "effective_start": start, "effective_end": end,
                        "min_base": min_val, "mid_base": mid_val, "max_base": max_val,
                        "currency": curr
                    })

    # Step 3 & 4: Master Employees & Time-Series Data
    employees, salary_records, evidence, anomalies, adjustments = [], [], [], [], []
    adj_counter = 1

    for i in range(1, scale + 1):
        emp_id = f"EMP-{i:06d}"
        role = random.choice(roles)
        level = random.choice(levels)
        loc = random.choice(locations)
        hire_year = random.choice([2021, 2022, 2023])
        hire_date = f"{hire_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        employees.append({
            "employee_id": emp_id, "role_id": role, "level_id": level,
            "location_id": loc, "hire_date": hire_date, "status": "ACTIVE"
        })

        for yr in [2023, 2024, 2025]:
            rec_id = f"SAL-{emp_id}-{yr}01"
            fte = 0.5 if (i % 23 == 0) else 1.0
            curr = band_currencies[loc]
            ref_band_id = f"BAND-{role}-{level}-{loc}-{yr}"

            matched_band = next(b for b in bands if b["band_id"] == ref_band_id)
            comp_ratio_baseline = random.uniform(0.85, 1.15)
            fte_salary = matched_band["mid_base"] * comp_ratio_baseline
            actual_salary = fte_salary * fte

            # Step 5: Inject Labeled Edge Cases
            anomaly_type = None
            if yr == 2025:
                if i % 80 == 1:
                    anomaly_type = "EXPIRED_BAND_COMPARISON"
                    ref_band_id = f"BAND-{role}-{level}-{loc}-2023"
                elif i % 80 == 2 and fte < 1.0:
                    anomaly_type = "FTE_IGNORED"
                elif i % 80 == 3 and loc == "LON":
                    anomaly_type = "CURRENCY_CONVERSION_MISSING"
                    curr = "USD"
                elif i % 80 == 4:
                    anomaly_type = "INCOMPARABLE_ROLE_GROUPING"
                    ref_band_id = f"BAND-SWE-L5-{loc}-{yr}"

            salary_records.append({
                "salary_record_id": rec_id, "employee_id": emp_id,
                "effective_date": f"{yr}-01-01", "base_salary": round(actual_salary, 2),
                "currency": curr, "fte": fte, "applied_band_id": ref_band_id
            })

            evidence.append({
                "evidence_id": f"EV-{emp_id}-{yr}", "employee_id": emp_id,
                "eval_year": yr, "rating": round(random.uniform(2.5, 5.0), 1),
                "tenure_months": (yr - hire_year) * 12 + 6
            })

            if yr == 2025 and i % 80 == 5:
                anomaly_type = "UNAPPROVED_ADJUSTMENT"
                adjustments.append({
                    "adj_id": f"ADJ-{yr}-{adj_counter:06d}", "employee_id": emp_id,
                    "proposed_increase": 15000.0, "status": "PENDING_APPROVAL",
                    "approval_trail": "HR_INITIATED"
                })
                adj_counter += 1

            if anomaly_type:
                anomalies.append({
                    "anomaly_id": f"ANOM-{len(anomalies)+1:06d}",
                    "employee_id": emp_id, "salary_record_id": rec_id,
                    "issue_type": anomaly_type,
                    "context": f"Year {yr} injected {anomaly_type}"
                })

    def save_csv(filename, fieldnames, data):
        with open(os.path.join(output_dir, filename), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    save_csv("compensation_bands.csv", bands[0].keys(), bands)
    save_csv("employees.csv", employees[0].keys(), employees)
    save_csv("salary_records.csv", salary_records[0].keys(), salary_records)
    save_csv("performance_evidence.csv", evidence[0].keys(), evidence)
    if adjustments:
        save_csv("adjustment_proposals.csv", adjustments[0].keys(), adjustments)
    save_csv("ground_truth.csv", anomalies[0].keys(), anomalies)

    print(f"Dataset generated in '{output_dir}': {len(employees)} employees, {len(salary_records)} salary records.")

def calculate_checksum(directory="./data"):
    hasher = hashlib.sha256()
    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".csv"):
            with open(os.path.join(directory, fname), "rb") as f:
                hasher.update(f.read())
    return hasher.hexdigest()

if __name__ == "__main__":
    generate_dataset()
    chk1 = calculate_checksum()
    print(f"Run 1 SHA-256 Checksum: {chk1}")
    generate_dataset()
    chk2 = calculate_checksum()
    print(f"Run 2 SHA-256 Checksum: {chk2}")
    assert chk1 == chk2, "Deterministic verification failed."
    print("Deterministic generation verified successfully.")
