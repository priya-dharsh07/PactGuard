import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

sys.path.insert(0, PROJECT_ROOT)

from nlp.extractor import extract_text, split_into_clauses
from nlp.inference.predict import predict_clause


def analyze_contract(file_bytes: bytes, filename: str) -> list[dict]:
    raw_text = extract_text(file_bytes, filename)
    clauses = split_into_clauses(raw_text)

    results = []

    for clause in clauses:
        prediction = predict_clause(clause)

        results.append({
            "clause": clause,
            "category": prediction["category"],
            "confidence": prediction["confidence"]
        })

    return results


if __name__ == "__main__":
    test_file = os.path.join(
        PROJECT_ROOT,
        "backend",
        "tests",
        "sample_contract.txt"
    )

    with open(test_file, "rb") as f:
        file_bytes = f.read()

    results = analyze_contract(
        file_bytes,
        "sample_contract.txt"
    )

    for i, result in enumerate(results, 1):
        print(f"\nCLAUSE {i}")
        print(f"Category   : {result['category']}")
        print(f"Confidence : {result['confidence']}")
        print(f"Text       : {result['clause'][:300]}")