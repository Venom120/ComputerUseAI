from __future__ import annotations

import json, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

import logging

logger = logging.getLogger(__name__)

try:
    from llama_cpp import Llama
except ImportError:
    logger.error("llama-cpp-python not installed. Please run 'pip install llama-cpp-python'")
    sys.exit()


@dataclass
class LLMConfig:
    model_path: Path = Path("models/phi-3-mini-4k-instruct-q4.gguf")
    context_size: int = 2048
    temperature: float = 0.3


class LocalLLM:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._llm: Optional[Llama] = None
        self._init()

    def _init(self) -> None:
        if Llama is None:
            logger.error("Cannot initialize LLM: llama_cpp not imported.")
            return
            
        model_file = self.config.model_path
        if not model_file.exists():
            logger.error(f"LLM model file not found: {model_file}")
            logger.error("Please run 'python tools/model_setup.py' to download the model.")
            return

        try:
            self._llm = Llama(
                model_path=str(model_file),
                n_ctx=self.config.context_size,
                n_threads=4, 
                verbose=False
            )
            logger.info(f"LLM loaded successfully: {model_file.name}")
        except Exception as e:
            logger.exception(f"Failed to load LLM model {model_file}: {e}")

    def analyze_workflow(self, screen_jsons: List[Dict[str, Any]], transcripts: List[str], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self._llm is None:
            logger.warning("LLM not loaded. Skipping workflow analysis.")
            return {"workflow_summary": "", "steps": [], "is_repetitive": False, "automation_potential": "low"}
        
        prompt = self._build_prompt(screen_jsons, transcripts, events)
        
        try:
            chat_messages = [
                {"role": "system", "content": "You are an expert AI assistant that analyzes user computer activity to understand their workflow. Respond ONLY with a valid JSON object matching the requested format."},
                {"role": "user", "content": prompt}
            ]

            response = self._llm.create_chat_completion(
                messages=chat_messages,  # type: ignore
                temperature=self.config.temperature,
                max_tokens=1024,
            )
            
            content = response['choices'][0]['message']['content'] # type: ignore
            if content is None:
                logger.error("LLM returned an empty message (content is None).")
                return {"workflow_summary": "LLM returned no content.", "steps": [], "is_repetitive": False, "automation_potential": "low"}
            
            text = content.strip()
            
            return self._safe_json(text)
        except Exception as e:
            logger.exception(f"LLM analysis error: {e}")
            return {"workflow_summary": "", "steps": [], "is_repetitive": False, "automation_potential": "low"}

    def _build_prompt(self, screen_jsons, transcripts, events) -> str:
        return (
            "Analyze the following user activity logs. Based ONLY on this data, "
            "describe the user's workflow, identify if it's repetitive, and "
            "list the key steps.\n\n"
            f"Screen States (brief summary):\n{json.dumps(screen_jsons, indent=2)}\n\n"
            f"Audio Commands:\n{'\n'.join(transcripts)}\n\n"
            f"Event Log:\n{json.dumps(events, indent=2)}\n\n"
            "Respond with a single JSON object with keys: "
            "\"workflow_summary\" (string), "
            "\"steps\" (list of strings), "
            "\"is_repetitive\" (boolean), "
            "\"automation_potential\" (string: 'low', 'medium', 'high')."
        )

    def _safe_json(self, text: str) -> Dict[str, Any]:
        import json

        text = text.strip()
        
        try:
            start = text.index('{')
            end = text.rindex('}') + 1
            json_text = text[start:end]
            return json.loads(json_text)
        except Exception:
            logger.warning(f"LLM did not return valid JSON. Response was: {text}")
            return {"workflow_summary": "LLM response was not valid JSON.", "steps": [], "is_repetitive": False, "automation_potential": "low"}