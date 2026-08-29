import os
import pickle
import numpy as np
import pandas as pd
import torch

from datasets import Dataset
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    DataCollatorWithPadding,
    TrainingArguments,
    Trainer
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models", "pactguard-legalbert")

MODEL_NAME = "nlpaueb/legal-bert-base-uncased"

train_df = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
val_df = pd.read_csv(os.path.join(DATA_DIR, "validation.csv"))
test_df = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))

label_encoder = LabelEncoder()

train_df["label_id"] = label_encoder.fit_transform(train_df["label"])
val_df["label_id"] = label_encoder.transform(val_df["label"])
test_df["label_id"] = label_encoder.transform(test_df["label"])

num_labels = len(label_encoder.classes_)

print("Train samples:", len(train_df))
print("Validation samples:", len(val_df))
print("Test samples:", len(test_df))
print("Number of classes:", num_labels)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=num_labels,
    id2label={
        i: label
        for i, label in enumerate(label_encoder.classes_)
    },
    label2id={
        label: i
        for i, label in enumerate(label_encoder.classes_)
    }
)

def tokenize_function(examples):
    return tokenizer(
        examples["clause_text"],
        truncation=True,
        max_length=512
    )

train_dataset = Dataset.from_pandas(
    train_df[["clause_text", "label_id"]],
    preserve_index=False
)

val_dataset = Dataset.from_pandas(
    val_df[["clause_text", "label_id"]],
    preserve_index=False
)

test_dataset = Dataset.from_pandas(
    test_df[["clause_text", "label_id"]],
    preserve_index=False
)

train_dataset = train_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["clause_text"]
)

val_dataset = val_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["clause_text"]
)

test_dataset = test_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["clause_text"]
)

train_dataset = train_dataset.rename_column("label_id", "labels")
val_dataset = val_dataset.rename_column("label_id", "labels")
test_dataset = test_dataset.rename_column("label_id", "labels")

data_collator = DataCollatorWithPadding(
    tokenizer=tokenizer,
    padding=True
)

def compute_metrics(eval_pred):
    predictions, labels = eval_pred

    predictions = np.argmax(predictions, axis=1)

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        predictions,
        average="weighted",
        zero_division=0
    )

    accuracy = accuracy_score(labels, predictions)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

training_args = TrainingArguments(
    output_dir=MODEL_DIR,
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    logging_steps=50,
    fp16=torch.cuda.is_available(),
    report_to="none"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    data_collator=data_collator,
    compute_metrics=compute_metrics
)

print("Training device:", "cuda" if torch.cuda.is_available() else "cpu")

trainer.train()

test_results = trainer.evaluate(test_dataset)

print("\nTest Results")
print(test_results)

trainer.save_model(MODEL_DIR)
tokenizer.save_pretrained(MODEL_DIR)

with open(
    os.path.join(MODEL_DIR, "label_encoder.pkl"),
    "wb"
) as f:
    pickle.dump(label_encoder, f)

print("\nModel saved to:")
print(MODEL_DIR)