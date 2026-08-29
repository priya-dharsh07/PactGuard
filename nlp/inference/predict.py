import os
import pickle
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models", "pactguard-legalbert")

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)

with open(os.path.join(MODEL_DIR, "label_encoder.pkl"), "rb") as f:
    label_encoder = pickle.load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

def predict_clause(clause_text):
    inputs = tokenizer(
        clause_text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():
        outputs = model(**inputs)

    probabilities = torch.softmax(outputs.logits, dim=-1)
    confidence, predicted_id = torch.max(probabilities, dim=-1)

    predicted_id = predicted_id.item()
    confidence = confidence.item()

    label = label_encoder.inverse_transform([predicted_id])[0]

    return {
        "clause": clause_text,
        "category": label,
        "confidence": round(confidence, 4)
    }

if __name__ == "__main__":
    clause = """
    Either party may terminate this Agreement for convenience
    upon thirty days prior written notice to the other party.
    """

    result = predict_clause(clause)

    print(result)