from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "nlp" / "data"

INPUT_FILE = DATA_DIR / "cuad_clause_dataset.csv"
TRAIN_FILE = DATA_DIR / "train.csv"
VALIDATION_FILE = DATA_DIR / "validation.csv"
TEST_FILE = DATA_DIR / "test.csv"

TARGET_TOTAL_CATEGORIES = 500
MIN_CLUSTER_SIZE = 12  # below this, a sub-category is too thin to learn reliably
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_TERMS_PER_CLUSTER = 3

LEGAL_STOPWORDS = {
    "shall", "party", "parties", "agreement", "section", "hereof", "hereto",
    "herein", "thereof", "pursuant", "provided", "including", "such",
    "means", "term", "terms", "provisions", "provision", "clause", "clauses",
    "date", "written", "notice", "respect", "accordance", "applicable",
    "set", "forth", "hereunder", "person", "persons", "used", "use",
}
CUSTOM_STOP_WORDS = list(ENGLISH_STOP_WORDS.union(LEGAL_STOPWORDS))


def name_cluster_tfidf(cluster_texts, other_cluster_texts_list):
    documents = ["\n".join(cluster_texts)] + ["\n".join(t) for t in other_cluster_texts_list]

    vectorizer = TfidfVectorizer(
        max_features=2000,
        stop_words=CUSTOM_STOP_WORDS,
        ngram_range=(1, 2),
        min_df=1,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return "variant"

    feature_names = vectorizer.get_feature_names_out()
    cluster_scores = tfidf_matrix[0].toarray().flatten()
    top_indices = cluster_scores.argsort()[::-1][:TOP_TERMS_PER_CLUSTER]

    top_terms = [feature_names[i] for i in top_indices if cluster_scores[i] > 0]
    if not top_terms:
        return "variant"

    label = "_".join(top_terms).replace(" ", "_")
    label = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in label)
    label = "_".join(filter(None, label.split("_")))
    return label if label else "variant"


def expand_categories(df: pd.DataFrame) -> pd.DataFrame:
    print(f"Loaded {len(df)} clauses across {df['label'].nunique()} broad categories")

    print("Computing embeddings (one-time, CPU is fine for this)...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embedder.encode(df["clause_text"].tolist(), show_progress_bar=True)

    total_rows = len(df)
    fine_labels = np.empty(total_rows, dtype=object)
    total_clusters_created = 0

    for broad_label, group in df.groupby("label"):
        idx = group.index.to_numpy()
        group_embeddings = embeddings[idx]
        count = len(idx)

        proportional_k = max(1, round(count / total_rows * TARGET_TOTAL_CATEGORIES))
        max_k_by_size = max(1, count // MIN_CLUSTER_SIZE)
        k = min(proportional_k, max_k_by_size)

        print(f"{broad_label}: {count} clauses -> {k} sub-categories")
        total_clusters_created += k

        if k == 1:
            fine_labels[idx] = broad_label
            continue

        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        cluster_ids = kmeans.fit_predict(group_embeddings)

        cluster_texts_by_id = {
            cid: df.loc[idx[cluster_ids == cid], "clause_text"].tolist()
            for cid in range(k)
        }

        used_names_for_label = set()

        for cluster_id in range(k):
            mask = cluster_ids == cluster_id
            cluster_row_idx = idx[mask]

            this_cluster_texts = cluster_texts_by_id[cluster_id]
            other_cluster_texts = [
                cluster_texts_by_id[cid] for cid in range(k) if cid != cluster_id
            ]

            sub_name = name_cluster_tfidf(this_cluster_texts, other_cluster_texts)

            # Guarantee uniqueness within this broad category
            final_name = sub_name
            suffix = 2
            while final_name in used_names_for_label:
                final_name = f"{sub_name}_{suffix}"
                suffix += 1
            used_names_for_label.add(final_name)

            fine_labels[cluster_row_idx] = f"{broad_label}__{final_name}"

    df = df.copy()
    df["label"] = fine_labels
    print(f"\nTotal clusters created: {total_clusters_created}")
    print(f"Expanded to {df['label'].nunique()} fine-grained categories")
    return df


def contract_level_split(df: pd.DataFrame, train_frac=0.7, val_frac=0.15, seed=42):
    """Splits by source_contract (not by row) so clauses from the same
    contract never appear in more than one split - avoids leakage."""
    rng = np.random.default_rng(seed)
    contracts = df["source_contract"].unique()
    rng.shuffle(contracts)

    n = len(contracts)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)

    train_contracts = set(contracts[:train_end])
    val_contracts = set(contracts[train_end:val_end])
    test_contracts = set(contracts[val_end:])

    train_df = df[df["source_contract"].isin(train_contracts)]
    val_df = df[df["source_contract"].isin(val_contracts)]
    test_df = df[df["source_contract"].isin(test_contracts)]

    return train_df, val_df, test_df


def main():
    df = pd.read_csv(INPUT_FILE)

    expanded_df = expand_categories(df)

    train_df, val_df, test_df = contract_level_split(expanded_df)

    # Drop any category that ended up with zero examples in train
    valid_labels = set(train_df["label"].unique())
    val_df = val_df[val_df["label"].isin(valid_labels)]
    test_df = test_df[test_df["label"].isin(valid_labels)]

    print(f"\nFinal split sizes:")
    print(f"  Train: {len(train_df)} rows, {train_df['label'].nunique()} categories")
    print(f"  Validation: {len(val_df)} rows, {val_df['label'].nunique()} categories")
    print(f"  Test: {len(test_df)} rows, {test_df['label'].nunique()} categories")

    train_df.to_csv(TRAIN_FILE, index=False, encoding="utf-8")
    val_df.to_csv(VALIDATION_FILE, index=False, encoding="utf-8")
    test_df.to_csv(TEST_FILE, index=False, encoding="utf-8")

    print(f"\nSaved:")
    print(f"  {TRAIN_FILE}")
    print(f"  {VALIDATION_FILE}")
    print(f"  {TEST_FILE}")


if __name__ == "__main__":
    main()