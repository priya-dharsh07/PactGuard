# nlp/preprocessing/prepare_dataset.py
import os
import re
from pathlib import Path
from collections import defaultdict

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
MIN_CLUSTER_SIZE = 12  
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


def load_raw_dataset() -> pd.DataFrame:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_FILE}. Please ensure 'cuad_clause_dataset.csv' exists in 'nlp/data/'."
        )

    print(f"Loading local dataset from: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)

    col_map = {}
    for col in df.columns:
        c_lower = col.lower().strip()
        if c_lower in ["clause_text", "text", "clause", "context"]:
            col_map[col] = "clause_text"
        elif c_lower in ["contract_name", "contract_id", "filename", "title", "contract"]:
            col_map[col] = "contract_name"
        elif c_lower in ["label", "category", "clause_type", "broad_category"]:
            col_map[col] = "label"

    df = df.rename(columns=col_map)

    if "clause_text" not in df.columns or "label" not in df.columns:
        raise ValueError(f"CSV must contain clause text and category columns. Found: {list(df.columns)}")

    if "contract_name" not in df.columns:
        print("[Warning] 'contract_name' column missing. Assigning row-based contract IDs.")
        df["contract_name"] = [f"contract_{i // 15}" for i in range(len(df))]

    df = df.dropna(subset=["clause_text", "label"])
    df["clause_text"] = df["clause_text"].astype(str).str.strip()
    df = df[df["clause_text"].str.len() >= 25].drop_duplicates(subset=["clause_text"]).reset_index(drop=True)
    return df

def expand_categories(df: pd.DataFrame) -> pd.DataFrame:

    print(f"Loaded {len(df)} clauses across {df['label'].nunique()} broad categories")
    print("Computing MiniLM sentence embeddings...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embedder.encode(df["clause_text"].tolist(), show_progress_bar=True, batch_size=64)

    broad_counts = df["label"].value_counts()
    total_samples = len(df)
    
    fine_grained_labels = [""] * len(df)
    seen_names = set()

    print("\nClustering broad categories into sub-categories...")
    for broad_cat, count in broad_counts.items():
        cat_indices = df[df["label"] == broad_cat].index.to_numpy()
        cat_texts = df.loc[cat_indices, "clause_text"].tolist()
        cat_embeds = embeddings[cat_indices]

        k = max(1, min(int(round((count / total_samples) * TARGET_TOTAL_CATEGORIES)), count // MIN_CLUSTER_SIZE))

        if k <= 1 or count < (MIN_CLUSTER_SIZE * 2):
            cluster_assignments = np.zeros(len(cat_indices), dtype=int)
            k = 1
        else:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=5)
            cluster_assignments = kmeans.fit_predict(cat_embeds)

        cluster_texts_dict = defaultdict(list)
        cluster_indices_dict = defaultdict(list)
        for sub_id, g_idx in zip(cluster_assignments, cat_indices):
            cluster_texts_dict[sub_id].append(df.loc[g_idx, "clause_text"])
            cluster_indices_dict[sub_id].append(g_idx)

        for sub_id in range(k):
            sub_texts = cluster_texts_dict[sub_id]
            sub_indices = cluster_indices_dict[sub_id]

            if k == 1:
                sub_label_tag = "standard"
            else:
                other_texts = [cluster_texts_dict[o_id] for o_id in range(k) if o_id != sub_id]
                sub_label_tag = name_cluster_tfidf(sub_texts, other_texts)

            clean_broad = str(broad_cat).lower().strip().replace(" ", "_").replace("-", "_")
            composite_name = f"{clean_broad}__{sub_label_tag}"

            unique_name = composite_name
            counter = 1
            while unique_name in seen_names:
                unique_name = f"{composite_name}_v{counter}"
                counter += 1
            seen_names.add(unique_name)

            for g_idx in sub_indices:
                fine_grained_labels[g_idx] = unique_name

    df["label"] = fine_grained_labels
    print(f"\nSuccessfully generated {df['label'].nunique()} fine-grained categories.")
    return df


def contract_level_split(df: pd.DataFrame, train_ratio=0.80, val_ratio=0.10):
    unique_contracts = df["contract_name"].unique()
    np.random.seed(42)
    np.random.shuffle(unique_contracts)

    n_total = len(unique_contracts)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_c = set(unique_contracts[:n_train])
    val_c = set(unique_contracts[n_train:n_train + n_val])
    test_c = set(unique_contracts[n_train + n_val:])

    train_df = df[df["contract_name"].isin(train_c)].copy()
    val_df = df[df["contract_name"].isin(val_c)].copy()
    test_df = df[df["contract_name"].isin(test_c)].copy()

    return train_df, val_df, test_df


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    df = load_raw_dataset()

    df = expand_categories(df)
    print("\nSplitting by contract...")
    train_df, val_df, test_df = contract_level_split(df)

    print(f"Train set:      {len(train_df)} clauses ({train_df['contract_name'].nunique()} contracts)")
    print(f"Validation set: {len(val_df)} clauses ({val_df['contract_name'].nunique()} contracts)")
    print(f"Test set:       {len(test_df)} clauses ({test_df['contract_name'].nunique()} contracts)")

    cols_to_save = ["contract_name", "clause_text", "label"]
    train_df[cols_to_save].to_csv(TRAIN_FILE, index=False)
    val_df[cols_to_save].to_csv(VALIDATION_FILE, index=False)
    test_df[cols_to_save].to_csv(TEST_FILE, index=False)

    print(f"\nSaved:")
    print(f"  -> {TRAIN_FILE}")
    print(f"  -> {VALIDATION_FILE}")
    print(f"  -> {TEST_FILE}")
    print("\nDataset preparation complete!")


if __name__ == "__main__":
    main()