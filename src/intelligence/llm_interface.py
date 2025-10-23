from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List

import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    model_path: Path = Path("models/phi-3-mini-4k-instruct-q4.gguf")
    context_size: int = 2048
    temperature: float = 0.3


class LocalLLM:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._llm = None
        self._init()

    def _init(self) -> None:
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM  # type: ignore
            import torch

            # Use a smaller model that works with transformers
            model_name = "microsoft/DialoGPT-small"  # Fallback to a smaller model
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForCausalLM.from_pretrained(model_name)
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            self._llm = {"tokenizer": self._tokenizer, "model": self._model}
            logger.info("LLM loaded: %s", model_name)
        except Exception as e:
            logger.error("Failed to load LLM: %s", e)

    def analyze_workflow(self, screen_jsons: List[Dict[str, Any]], transcripts: List[str], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self._llm is None:
            return {"workflow_summary": "", "steps": [], "is_repetitive": False, "automation_potential": "low"}
        prompt = self._build_prompt(screen_jsons, transcripts, events)
        try:
            inputs = self._llm["tokenizer"].encode(prompt, return_tensors="pt", truncation=True, max_length=1024)
            with torch.no_grad():
                outputs = self._llm["model"].generate(
                    inputs,
                    max_length=inputs.shape[1] + 100,
                    temperature=self.config.temperature,
                    do_sample=True,
                    pad_token_id=self._llm["tokenizer"].eos_token_id
                )
            text = self._llm["tokenizer"].decode(outputs[0], skip_special_tokens=True)
            # Extract only the new generated text
            text = text[len(prompt):].strip()
            return self._safe_json(text)
        except Exception as e:
            logger.exception("LLM analysis error: %s", e)
            return {"workflow_summary": "", "steps": [], "is_repetitive": False, "automation_potential": "low"}

    def _build_prompt(self, screen_jsons, transcripts, events) -> str:
        return (
            "You are analyzing user computer activity to understand their workflow.\n\n"
            f"Screen States:\n```json\n{screen_jsons}\n```\n\n"
            f"Audio Commands:\n```\n{'\n'.join(transcripts)}\n```\n\n"
            f"Event Log:\n```json\n{events}\n```\n\n"
            "Task: Describe what the user did in clear steps. Identify if this is a repetitive pattern.\n"
            "Format your response as JSON with keys workflow_summary, steps, is_repetitive, automation_potential."
        )

    def _safe_json(self, text: str) -> Dict[str, Any]:
        import json

        text = text.strip()
        # Attempt to extract JSON
        try:
            if text.startswith("```)" ):
                text = text.strip("` ")
            return json.loads(text)
        except Exception:
            return {"workflow_summary": text[:200], "steps": [], "is_repetitive": False, "automation_potential": "low"}


