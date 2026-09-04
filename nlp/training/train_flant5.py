# nlp/training/train_flant5.py
import os
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "nlp" / "data"
MODEL_DIR = PROJECT_ROOT / "models" / "pactguard-flant5"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "google/flan-t5-base"
INSTRUCTION = "Identify the type of this legal contract clause in a few words.\n\nClause: "
MAX_INPUT_LENGTH = 512
MAX_TARGET_LENGTH = 32

def format_targets(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["input_text"] = INSTRUCTION + df["clause_text"].astype(str)
    df["target_text"] = (
        df["label"]
        .astype(str)
        .str.replace("__", " - ")
        .str.replace("_", " ")
        .str.strip()
        .str.lower()
    )
    return df

def main():
    print("--- Training Flan-T5 Locally ---")
    train_path = DATA_DIR / "train.csv"
    val_path = DATA_DIR / "validation.csv"
    test_path = DATA_DIR / "test.csv"

    if not train_path.exists():
        raise FileNotFoundError(f"Missing {train_path}. Run prepare_dataset.py first.")

    train_df = format_targets(pd.read_csv(train_path))
    val_df = format_targets(pd.read_csv(val_path))
    test_df = format_targets(pd.read_csv(test_path))

    print(f"Train samples: {len(train_df)} | Unique categories: {train_df['target_text'].nunique()}")
    print(f"Validation samples: {len(val_df)} | Test samples: {len(test_df)}")

    # Load Tokenizer & Model
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
        broad_preds = [p.split(" - ")[0].strip() for p in decoded_preds]
        broad_labels = [l.split(" - ")[0].strip() for l in decoded_labels]
        broad_match = np.mean([p == l for p, l in zip(broad_preds, broad_labels)])

        return {"exact_match": exact_match, "broad_match": broad_match}

    has_cuda = torch.cuda.is_available()
    use_bf16 = has_cuda and torch.cuda.is_bf16_supported()

    # Local training settings (lighter batch size to prevent OOM)
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(MODEL_DIR),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=3e-4,
        per_device_train_batch_size=4 if has_cuda else 2,
        per_device_eval_batch_size=4 if has_cuda else 2,
        gradient_accumulation_steps=4 if has_cuda else 8,
        num_train_epochs=3,
        weight_decay=0.01,
        warmup_ratio=0.05,
        max_grad_norm=1.0,           # Prevents NaN
        predict_with_generate=True,
        generation_max_length=MAX_TARGET_LENGTH,
        load_best_model_at_end=True,
        metric_for_best_model="exact_match",
        logging_steps=25,
        bf16=use_bf16,
        fp16=False,                  # Prevents NaN
        report_to="none",
        save_total_limit=1
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

    print(f"Training on: {'cuda' if has_cuda else 'cpu'} (bf16={use_bf16})...")
    trainer.train()

    print("\nEvaluating on Test Set...")
    test_metrics = trainer.evaluate(test_dataset)
    print("Test Set Metrics:", test_metrics)

    trainer.save_model(str(MODEL_DIR))
    tokenizer.save_pretrained(str(MODEL_DIR))
    print(f"\nModel and Tokenizer successfully saved to: {MODEL_DIR}")

if __name__ == "__main__":
    main()