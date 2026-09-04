# nlp/training/train_tfidf_svm.py
import os
import joblib
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "nlp" / "data"
MODEL_DIR = PROJECT_ROOT / "nlp" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_FILE = DATA_DIR / "train.csv"
VAL_FILE = DATA_DIR / "validation.csv"
TEST_FILE = DATA_DIR / "test.csv"
OUTPUT_MODEL_PATH = MODEL_DIR / "tfidf_svm.joblib"

def main():
    print("--- Training TF-IDF + Linear SVM Baseline ---")
    if not TRAIN_FILE.exists():
        raise FileNotFoundError(f"Missing {TRAIN_FILE}. Please run 'python nlp/preprocessing/prepare_dataset.py' first.")

    print("Loading CSV files...")
    train_df = pd.read_csv(TRAIN_FILE)
    val_df = pd.read_csv(VAL_FILE)
    test_df = pd.read_csv(TEST_FILE)

    X_train, y_train = train_df["clause_text"].astype(str), train_df["label"].astype(str)
    X_val, y_val = val_df["clause_text"].astype(str), val_df["label"].astype(str)
    X_test, y_test = test_df["clause_text"].astype(str), test_df["label"].astype(str)

    print(f"Loaded: {len(X_train)} train, {len(X_val)} validation, {len(X_test)} test samples.")
    print(f"Total categories: {y_train.nunique()}")

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=25000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english"
        )),
        ("svm", LinearSVC(C=1.0, max_iter=3000, random_state=42))
    ])

    pipeline.fit(X_train, y_train)

    val_preds = pipeline.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)
    print(f"\n[Validation Set] Exact Accuracy: {val_acc * 100:.2f}%")

    test_preds = pipeline.predict(X_test)
    test_acc = accuracy_score(y_test, test_preds)
    print(f"[Test Set]       Exact Accuracy: {test_acc * 100:.2f}%")

    test_broad_true = [y.split("__")[0].split(" - ")[0].strip() for y in y_test]
    test_broad_pred = [p.split("__")[0].split(" - ")[0].strip() for p in test_preds]
    broad_acc = accuracy_score(test_broad_true, test_broad_pred)
    print(f"[Test Set]       Broad Category Accuracy: {broad_acc * 100:.2f}%")

    joblib.dump(pipeline, OUTPUT_MODEL_PATH)
    print(f"\nModel successfully saved to: {OUTPUT_MODEL_PATH}")

if __name__ == "__main__":
    main()