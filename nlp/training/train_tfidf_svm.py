from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.svm import LinearSVC


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "nlp" / "data"
MODEL_DIR = PROJECT_ROOT / "nlp" / "models"

TRAIN_FILE = DATA_DIR / "train.csv"
VALIDATION_FILE = DATA_DIR / "validation.csv"
TEST_FILE = DATA_DIR / "test.csv"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("Loading datasets...")

    train_df = pd.read_csv(TRAIN_FILE)
    validation_df = pd.read_csv(VALIDATION_FILE)
    test_df = pd.read_csv(TEST_FILE)

    X_train = train_df["clause_text"].fillna("")
    y_train = train_df["label"]

    X_validation = validation_df["clause_text"].fillna("")
    y_validation = validation_df["label"]

    X_test = test_df["clause_text"].fillna("")
    y_test = test_df["label"]

    print(f"Training samples: {len(X_train)}")
    print(f"Validation samples: {len(X_validation)}")
    print(f"Test samples: {len(X_test)}")

    print("\nCreating TF-IDF features...")

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
        max_features=100000,
    )

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_validation_tfidf = vectorizer.transform(X_validation)
    X_test_tfidf = vectorizer.transform(X_test)

    print(f"TF-IDF features: {X_train_tfidf.shape[1]}")

    print("\nTraining SVM...")

    model = LinearSVC(
        class_weight="balanced",
        C=1.0,
        random_state=42,
    )

    model.fit(X_train_tfidf, y_train)

    print("\nEvaluating validation set...")

    validation_predictions = model.predict(X_validation_tfidf)

    validation_accuracy = accuracy_score(
        y_validation,
        validation_predictions,
    )

    print(f"Validation accuracy: {validation_accuracy:.4f}")

    print("\nValidation classification report:")

    print(
        classification_report(
            y_validation,
            validation_predictions,
            zero_division=0,
        )
    )

    print("\nEvaluating test set...")

    test_predictions = model.predict(X_test_tfidf)

    test_accuracy = accuracy_score(
        y_test,
        test_predictions,
    )

    print(f"Test accuracy: {test_accuracy:.4f}")

    print("\nTest classification report:")

    print(
        classification_report(
            y_test,
            test_predictions,
            zero_division=0,
        )
    )

    vectorizer_path = MODEL_DIR / "tfidf_vectorizer.joblib"
    model_path = MODEL_DIR / "svm_classifier.joblib"

    joblib.dump(vectorizer, vectorizer_path)
    joblib.dump(model, model_path)

    print("\nModels saved:")

    print(vectorizer_path)
    print(model_path)


if __name__ == "__main__":
    main()