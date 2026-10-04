from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]

QUESTIONS = (
    ROOT
    / "data"
    / "raw"
    / "maple_data"
    / "maple_collections_release"
    / "data"
    / "benchmark_questions.csv"
)

SUBMISSIONS = [
    ROOT / "data" / "benchmark_answers.csv",
    ROOT
    / "data"
    / "raw"
    / "maple_data"
    / "maple_collections_release"
    / "labels"
    / "benchmark_answers_submission.csv",
]

REQUIRED_COLUMNS = {"question_id", "answer", "sql_or_sources", "refused"}

EXPECTED_REFUSALS = {
    "BQ-018",
    "BQ-023",
    "BQ-024",
    "BQ-029",
    "BQ-031",
}


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validate(path, expected_ids):
    print(f"\nChecking: {path.relative_to(ROOT)}")

    if not path.exists():
        print("FAIL: file does not exist")
        return False

    rows = read_csv(path)
    ok = True

    if not rows:
        print("FAIL: file is empty")
        return False

    columns = set(rows[0].keys())
    missing_columns = REQUIRED_COLUMNS - columns

    if missing_columns:
        print(f"FAIL: missing columns: {sorted(missing_columns)}")
        ok = False
    else:
        print("PASS: required columns present")

    ids = [row["question_id"] for row in rows]
    id_set = set(ids)

    duplicates = sorted(
        {question_id for question_id in ids if ids.count(question_id) > 1}
    )
    missing_ids = sorted(expected_ids - id_set)
    unexpected_ids = sorted(id_set - expected_ids)

    if duplicates:
        print(f"FAIL: duplicate IDs: {duplicates}")
        ok = False
    else:
        print("PASS: no duplicate question IDs")

    if missing_ids:
        print(f"FAIL: missing IDs: {missing_ids}")
        ok = False
    else:
        print("PASS: no missing question IDs")

    if unexpected_ids:
        print(f"FAIL: unexpected IDs: {unexpected_ids}")
        ok = False
    else:
        print("PASS: no unexpected question IDs")

    empty_answers = [
        row["question_id"]
        for row in rows
        if not row.get("answer", "").strip()
    ]

    if empty_answers:
        print(f"FAIL: empty answers: {empty_answers}")
        ok = False
    else:
        print("PASS: every question has an answer")

    actual_refusals = {
        row["question_id"]
        for row in rows
        if row.get("refused", "").strip().lower() == "true"
    }

    if actual_refusals == EXPECTED_REFUSALS:
        print("PASS: refusal flags match expected governance cases")
    else:
        print(f"FAIL: expected refusals: {sorted(EXPECTED_REFUSALS)}")
        print(f"      actual refusals:   {sorted(actual_refusals)}")
        ok = False

    if len(rows) == len(expected_ids):
        print(f"PASS: row count = {len(rows)}")
    else:
        print(
            f"FAIL: expected {len(expected_ids)} rows, found {len(rows)}"
        )
        ok = False

    return ok


def main():
    questions = read_csv(QUESTIONS)
    expected_ids = {row["question_id"] for row in questions}

    print(f"Expected benchmark questions: {len(expected_ids)}")

    if len(expected_ids) != 35:
        print(
            f"WARNING: expected 35 benchmark questions, "
            f"dataset contains {len(expected_ids)}"
        )

    all_ok = True

    for submission in SUBMISSIONS:
        if not validate(submission, expected_ids):
            all_ok = False

    print("\n" + "=" * 60)

    if all_ok:
        print("BENCHMARK VALIDATION: PASS")
        return 0

    print("BENCHMARK VALIDATION: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())