import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models", "pactguard-flant5")

INSTRUCTION = (
    "Identify the type of this legal contract clause in a few words.\n\nClause: "
)
MAX_TARGET_LENGTH = 16

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_DIR)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()


def predict_clause(clause_text):
    inputs = tokenizer(
        INSTRUCTION + clause_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_TARGET_LENGTH,
            output_scores=True,
            return_dict_in_generate=True,
        )

    generated_ids = outputs.sequences[0]
    label = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

    confidence = _sequence_confidence(outputs)

    return {
        "clause": clause_text,
        "category": label.replace(" ", "_") if label else "unclassified",
        "confidence": round(confidence, 4),
    }


def _sequence_confidence(generate_outputs) -> float:
    if not generate_outputs.scores:
        return 0.0
    probs = []
    for step_scores in generate_outputs.scores:
        step_probs = torch.softmax(step_scores[0], dim=-1)
        probs.append(step_probs.max().item())
    return sum(probs) / len(probs) if probs else 0.0


if __name__ == "__main__":
    clause = """
    Either party may terminate this Agreement for convenience
    upon thirty days prior written notice to the other party.
    """
    result = predict_clause(clause)
    print(result)