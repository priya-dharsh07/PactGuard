import os
import numpy as np
import pandas as pd
import torch

from datasets import Dataset

from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)

DATA_DIR = os.path.expanduser("~/data")
MODEL_DIR = os.path.expanduser("~/models/pactguard-flant5")

MODEL_NAME = "google/flan-t5-base"

INSTRUCTION = (
    "Identify the type of this legal contract clause in a few words.\n\nClause: "
)
MAX_INPUT_LENGTH = 512
MAX_TARGET_LENGTH = 24

train_df = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
val_df = pd.read_csv(os.path.join(DATA_DIR, "validation.csv"))
test_df = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))


def to_prompted(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["input_text"] = INSTRUCTION + df["clause_text"]
    df["target_text"] = df["label"].str.replace("__", " - ").str.replace("_", " ")
    return df


train_df = to_prompted(train_df)
val_df = to_prompted(val_df)
test_df = to_prompted(test_df)

print("Train samples:", len(train_df))
print("Validation samples:", len(val_df))
print("Test samples:", len(test_df))
print("Unique clause types seen during training:", train_df["label"].nunique())

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)


def tokenize_function(examples):
    model_inputs = tokenizer(
        examples["input_text"],
        truncation=True,
        max_length=MAX_INPUT_LENGTH,
    )
    labels = tokenizer(
        text_target=examples["target_text"],
        truncation=True,
        max_length=MAX_TARGET_LENGTH,
    )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


train_dataset = Dataset.from_pandas(train_df[["input_text", "target_text"]], preserve_index=False)
val_dataset = Dataset.from_pandas(val_df[["input_text", "target_text"]], preserve_index=False)
test_dataset = Dataset.from_pandas(test_df[["input_text", "target_text"]], preserve_index=False)

train_dataset = train_dataset.map(tokenize_function, batched=True, remove_columns=["input_text", "target_text"])
val_dataset = val_dataset.map(tokenize_function, batched=True, remove_columns=["input_text", "target_text"])
test_dataset = test_dataset.map(tokenize_function, batched=True, remove_columns=["input_text", "target_text"])

data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)


def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    if isinstance(predictions, tuple):
        predictions = predictions[0]

    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)

    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

    decoded_preds = [p.strip().lower() for p in decoded_preds]
    decoded_labels = [l.strip().lower() for l in decoded_labels]

    exact_match = np.mean([p == l for p, l in zip(decoded_preds, decoded_labels)])
    return {"exact_match": exact_match}


use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()

training_args = Seq2SeqTrainingArguments(
    output_dir=MODEL_DIR,
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=3e-4,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=4,
    weight_decay=0.01,
    predict_with_generate=True,
    generation_max_length=MAX_TARGET_LENGTH,
    load_best_model_at_end=True,
    metric_for_best_model="exact_match",
    logging_steps=50,
    bf16=use_bf16,
    fp16=False,  
    report_to="none",
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    data_collator=data_collator,
    processing_class=tokenizer,
    compute_metrics=compute_metrics,
)

print("Training device:", "cuda" if torch.cuda.is_available() else "cpu")
print("Using bf16:", use_bf16)

trainer.train()

test_results = trainer.evaluate(test_dataset)
print("\nTest Results")
print(test_results)

trainer.save_model(MODEL_DIR)
tokenizer.save_pretrained(MODEL_DIR)

print("\nModel saved to:")
print(MODEL_DIR)