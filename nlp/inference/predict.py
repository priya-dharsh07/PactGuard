# nlp/inference/predict.py
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_MODEL_NAME = "google/flan-t5-base"
INSTRUCTION = "Identify the type of this legal contract clause in a few words.\n\nClause: "

def find_model_path() -> Optional[Path]:
    candidate_roots = [
        PROJECT_ROOT / "nlp" / "models" / "pactguard-flant5",
        PROJECT_ROOT / "nlp" / "models",
        PROJECT_ROOT / "models" / "pactguard-flant5",
        PROJECT_ROOT / "models",
    ]

    for root in candidate_roots:
        if root.exists():
            for p in root.rglob("config.json"):
                return p.parent
    return None

class ClausePredictor:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        self.is_loaded = False
        self._load_model()

    def _load_model(self):
        model_dir = find_model_path()
        if not model_dir:
            print("[PactGuard] ❌ Could not find 'config.json' in 'nlp/models/'. Using fallback.")
            return

        try:
            print(f"[PactGuard] 🚀 Loading fine-tuned Flan-T5 from '{model_dir}' on {self.device}...")
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

            # Load tokenizer (from local folder if present, or base Flan-T5)
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            except Exception:
                self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)

            # Load your fine-tuned model weights
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                str(model_dir),
                torch_dtype=torch.float32
            ).to(self.device)
            self.model.eval()
            self.is_loaded = True
            print("[PactGuard] ✅ Flan-T5 AI Model loaded and ready for live inference!")
        except Exception as e:
            print(f"[PactGuard] ❌ Error loading weights: {e}")
            self.is_loaded = False

    def _format_category(self, raw_label: str) -> Dict[str, str]:
        raw = raw_label.strip()
        if " - " in raw:
            parts = raw.split(" - ", 1)
            display = parts[0].replace("_", " ").strip().title()
            sub = parts[1].replace("_", " ").strip()
        elif "__" in raw:
            parts = raw.split("__", 1)
            display = parts[0].replace("_", " ").strip().title()
            sub = parts[1].replace("_", " ").strip()
        else:
            display = raw.replace("_", " ").strip().title()
            sub = ""

        return {
            "display_category": display if display else "General Provision",
            "subcategory": sub,
            "raw_output": raw
        }

    def predict_clause(self, clause_text: str) -> Dict[str, Any]:
        if not self.is_loaded:
            return self._heuristic_fallback(clause_text)

        prompt = INSTRUCTION + clause_text.strip()
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=32,
                return_dict_in_generate=True,
                output_scores=True
            )

        raw_pred = self.tokenizer.decode(outputs.sequences[0], skip_special_tokens=True).strip()

        # Compute confidence score
        try:
            transition_scores = self.model.compute_transition_scores(
                outputs.sequences, outputs.scores, normalize_logits=True
            )
            token_probs = torch.exp(transition_scores[0])
            confidence = float(torch.mean(token_probs).item())
            confidence = max(0.40, min(0.99, round(confidence, 2)))
        except Exception:
            confidence = 0.92

        formatted = self._format_category(raw_pred)

        return {
            "clause_type": formatted["display_category"],
            "raw_category": formatted["raw_output"],
            "subcategory": formatted["subcategory"],
            "confidence": confidence
        }

    def _heuristic_fallback(self, clause_text: str) -> Dict[str, Any]:
        text = clause_text.lower()
        if any(w in text for w in ["land", "parcel", "deed", "title", "encumbrance"]):
            cat = "Title & Real Property"
        elif any(w in text for w in ["contingenc", "due diligence", "inspection"]):
            cat = "Contingencies & Due Diligence"
        elif any(w in text for w in ["closing", "possession", "settlement"]):
            cat = "Closing & Possession"
        elif any(w in text for w in ["purchase price", "deposit", "earnest money", "escrow", "payment"]):
            cat = "Purchase Price & Payment Terms"
        elif any(w in text for w in ["governing law", "jurisdiction"]):
            cat = "Governing Law"
        elif any(w in text for w in ["indemn"]):
            cat = "Indemnification"
        else:
            cat = "General Provision"

        return {
            "clause_type": cat,
            "raw_category": cat.lower(),
            "subcategory": "",
            "confidence": 0.65
        }

_predictor_instance = None

def get_predictor() -> ClausePredictor:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = ClausePredictor()
    return _predictor_instance