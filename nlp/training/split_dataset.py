from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "nlp" / "data"

INPUT_FILE = DATA_DIR / "cuad_clause_dataset.csv"

TRAIN_FILE = DATA_DIR / "train.csv"
VALIDATION_FILE = DATA_DIR / "validation.csv"
TEST_FILE = DATA_DIR / "test.csv"

RANDOM_STATE = 42

TRAIN_SIZE = 0.70
VALIDATION_SIZE = 0.15
TEST_SIZE = 0.15

def main():

    df = pd.read_csv(INPUT_FILE)

    print(f"Total samples: {len(df)}")
    print(f"Unique contracts: {df['source_contract'].nunique()}")

    contracts = df["source_contract"].unique()

    train_contracts, temp_contracts = train_test_split(
        contracts,
        test_size=(VALIDATION_SIZE + TEST_SIZE),
        random_state=RANDOM_STATE,
    )

    validation_contracts, test_contracts = train_test_split(
        temp_contracts,
        test_size=0.5,
        random_state=RANDOM_STATE,
    )
    train_df = df[
        df["source_contract"].isin(train_contracts)
    ].copy()

    validation_df = df[
        df["source_contract"].isin(validation_contracts)
    ].copy()

    test_df = df[
        df["source_contract"].isin(test_contracts)
    ].copy()

    train_df.to_csv(
        TRAIN_FILE,
        index=False,
        encoding="utf-8",
    )

    validation_df.to_csv(
        VALIDATION_FILE,
        index=False,
        encoding="utf-8",
    )

    test_df.to_csv(
        TEST_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("DATASET SPLIT COMPLETE")
    print("=" * 60)

    print(
        f"\nTrain:"
        f"\n  Contracts: {len(train_contracts)}"
        f"\n  Clauses:   {len(train_df)}"
    )

    print(
        f"\nValidation:"
        f"\n  Contracts: {len(validation_contracts)}"
        f"\n  Clauses:   {len(validation_df)}"
    )

    print(
        f"\nTest:"
        f"\n  Contracts: {len(test_contracts)}"
        f"\n  Clauses:   {len(test_df)}"
    )
    train_set = set(train_contracts)
    validation_set = set(validation_contracts)
    test_set = set(test_contracts)

    print("\nContract overlap check:")

    print(
        "Train ∩ Validation:",
        len(train_set & validation_set),
    )

    print(
        "Train ∩ Test:",
        len(train_set & test_set),
    )

    print(
        "Validation ∩ Test:",
        len(validation_set & test_set),
    )

    print("\nTraining class distribution:")

    print(
        train_df["label"]
        .value_counts()
        .sort_index()
    )

    print("\nValidation class distribution:")

    print(
        validation_df["label"]
        .value_counts()
        .sort_index()
    )

    print("\nTest class distribution:")

    print(
        test_df["label"]
        .value_counts()
        .sort_index()
    )
    print("\nFiles saved:")
    print(TRAIN_FILE)
    print(VALIDATION_FILE)
    print(TEST_FILE)

if __name__ == "__main__":
    main()