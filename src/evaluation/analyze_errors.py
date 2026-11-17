
import json
from pathlib import Path
from collections import defaultdict, Counter

BASE_DIR = Path(__file__).resolve().parents[2]
FILE = BASE_DIR / "data" / "llm_evaluation_results.json"

with open(FILE, "r", encoding="utf-8") as f:
    records = json.load(f)

groups = defaultdict(list)

for record in records:
    groups[(record["experiment"], record["category"])].append(record)

print("\nCATEGORY-WISE PERFORMANCE")
print("=" * 65)

for (experiment, category), items in sorted(groups.items()):
    total = len(items)
    correct = sum(x["result_match"] for x in items)
    executed = sum(x["execution_success"] for x in items)

    print(
        f"{experiment:18} | {category:15} | "
        f"Correct: {correct}/{total} | "
        f"Executed: {executed}/{total}"
    )

print("\nERROR CLASSIFICATION")
print("=" * 65)

for experiment in sorted(set(x["experiment"] for x in records)):
    items = [x for x in records if x["experiment"] == experiment]
    counts = Counter(
        x["error_type"] for x in items
        if not x["result_match"]
    )

    print("\n", experiment)
    for error, count in counts.items():
        print(f"{error}: {count}")

print("\nSAMPLE INCORRECT QUERIES")
print("=" * 65)

for experiment in sorted(set(x["experiment"] for x in records)):
    print("\n", experiment)
    failed = [
        x for x in records
        if x["experiment"] == experiment and not x["result_match"]
    ]

    for item in failed[:5]:
        print(f"\nQuestion {item['id']}: {item['question']}")
        print("Generated SQL:", item["generated_sql"])
        print("Error:", item["error_type"])
        print("Details:", item["error"])
