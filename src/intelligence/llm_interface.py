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
    logger.error(
        "llama-cpp-python not found. LLM functionality will be disabled. "
        "Install it with: pip install llama-cpp-python"
    )
    sys.exit()


@dataclass
class LLMConfig:
    model_path: Path = Path("models/phi-3-mini-4k-instruct-q4.gguf")
    context_size: int = 4096 # Increased context size for more data
    temperature: float = 0.2 # Slightly lower temperature for more deterministic output
    n_gpu_layers: int = -1 # Use -1 to offload all possible layers to GPU


class LocalLLM:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._llm: Optional[Llama] = None
        self._init()

    def _init(self) -> None:
        if Llama is None:
            logger.error("Cannot initialize LLM: llama_cpp could not be imported.")
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
                n_threads=4, # Keep threads reasonable, more isn't always better
                n_gpu_layers=self.config.n_gpu_layers, # Offload layers
                verbose=False # Keep logs cleaner
            )
            logger.info(f"LLM loaded successfully: {model_file.name}")
        except Exception as e:
            logger.exception(f"Failed to load LLM model {model_file}: {e}")
            self._llm = None # Ensure _llm is None on failure

    # --- MODIFIED: Added events_for_llm parameter ---
    def analyze_workflow(self, screen_jsons: List[Dict[str, Any]], transcripts: List[str], events_for_llm: List[Dict[str, Any]]) -> Dict[str, Any]:
        default_response = {"workflow_summary": "", "steps": [], "is_repetitive": False, "automation_potential": "low"}
        if self._llm is None:
            logger.warning("LLM not loaded. Skipping workflow analysis.")
            return default_response.copy()

        # --- MODIFIED: Pass events_for_llm to _build_prompt ---
        prompt = self._build_prompt(screen_jsons, transcripts, events_for_llm)

        # --- Added safety check for prompt length ---
        # Estimate token count (very rough approximation)
        estimated_tokens = len(prompt) // 3
        if estimated_tokens >= self.config.context_size * 0.9: # Use 90% threshold
             logger.warning(f"Prompt length ({estimated_tokens} tokens) is close to context size ({self.config.context_size}). Truncating input data.")
             # Simple truncation strategy: keep fewer screens/events/transcripts
             keep_n = max(1, len(screen_jsons) // 2)
             screen_jsons = screen_jsons[-keep_n:]
             transcripts = transcripts[-keep_n:]
             events_for_llm = events_for_llm[-(keep_n*5):] # Keep more events relative to screens
             prompt = self._build_prompt(screen_jsons, transcripts, events_for_llm)


        try:
            # More specific system prompt
            system_prompt = (
                "You are an AI assistant analyzing user interaction logs (screen OCR, audio transcripts, UI events). "
                "Your goal is to identify and describe workflows, focusing on repetitive patterns. "
                "Provide a concise summary, list the distinct steps involved, determine if the overall pattern seems repetitive, "
                "and estimate its automation potential. "
                "Respond ONLY with a valid JSON object containing keys: "
                "'workflow_summary' (string, concise description, e.g., 'Filling expense report in Excel'), "
                "'steps' (list of strings, describing each distinct action, e.g., ['Click Save button', 'Type filename', 'Press Enter']), "
                "'is_repetitive' (boolean, true if the sequence of actions seems repeated), "
                "'automation_potential' (string: 'low', 'medium', 'high'). "
                "Be factual and base your analysis strictly on the provided logs."
            )
            chat_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

            logger.debug(f"Sending prompt to LLM (approx {len(prompt)} chars)...")
            response = self._llm.create_chat_completion(
                messages=chat_messages, # type: ignore
                temperature=self.config.temperature,
                max_tokens=1024, # Limit response size
                # Consider adding stop tokens if needed, e.g., stop=["}"]
            )

            # Defensive checking of response structure
            if not response or 'choices' not in response or not response['choices']: # type: ignore
                 logger.error("LLM response missing 'choices'.")
                 return default_response.copy()

            choice = response['choices'][0] # type: ignore
            if not choice or 'message' not in choice or 'content' not in choice['message']:
                 logger.error("LLM response choice structure invalid or content missing.")
                 return default_response.copy()

            content = choice['message']['content']
            if content is None:
                logger.error("LLM returned an empty message (content is None).")
                return {"workflow_summary": "LLM returned no content.", **default_response} # Add specific error

            text = content.strip()
            logger.debug(f"LLM raw response: {text[:500]}...") # Log beginning of response
            return self._safe_json(text)

        except Exception as e:
            logger.exception(f"LLM analysis error: {e}")
            return default_response.copy()

    # --- MODIFIED: Added events_for_llm parameter ---
    def _build_prompt(self, screen_jsons: List[Dict[str, Any]], transcripts: List[str], events_for_llm: List[Dict[str, Any]]) -> str:
        # --- MODIFIED: Simplified data representation for prompt ---
        # Summarize screens: just app, window title, and maybe first few text items
        screen_summaries = []
        for s in screen_jsons:
             summary = f"- App: {s.get('application', 'N/A')}, Title: {s.get('window_title', 'N/A')}"
             # visible_text = s.get('visible_text', [])
             # if visible_text:
             #      summary += f", Text Sample: {' | '.join(visible_text[:3])}"
             screen_summaries.append(summary)

        # Format events concisely
        event_summaries = [
            f"- {e.get('ts', '')}: {e.get('type', 'N/A')} in '{e.get('app', 'N/A')}' ({e.get('details', {})})"
            for e in events_for_llm
        ]

        prompt_parts = [
            "Analyze the following user activity logs recorded sequentially. Identify the primary workflow, list its key steps, determine if it's repetitive, and estimate automation potential.\n",
            "=== Screen States (App & Window Title) ===" ,
            "\n".join(screen_summaries) if screen_summaries else "No screen data.",
            "\n=== Audio Transcripts ===",
            "\n".join(f"- {t}" for t in transcripts) if transcripts else "No audio transcripts.",
            "\n=== UI Events ===",
            "\n".join(event_summaries) if event_summaries else "No UI events.",
            "\n=== Analysis Request ===",
            "Based ONLY on the logs above, provide your analysis as a single JSON object with keys: 'workflow_summary', 'steps' (list of strings), 'is_repetitive' (boolean), 'automation_potential' ('low'/'medium'/'high')."
        ]
        return "\n".join(prompt_parts)


    def _safe_json(self, text: str) -> Dict[str, Any]:
        """Attempts to parse JSON, cleaning common LLM output issues."""
        text = text.strip()
        logger.debug(f"Attempting to parse JSON from: {text[:500]}...")

        # Find the start and end of the JSON object
        try:
            start = text.index('{')
            end = text.rindex('}') + 1
            json_text = text[start:end]
        except ValueError:
            logger.warning(f"Could not find JSON object markers '{{' or '}}' in LLM response: {text[:500]}...")
            return {"workflow_summary": "LLM response did not contain JSON object.", "steps": [], "is_repetitive": False, "automation_potential": "low"}

        # Attempt to parse
        try:
            parsed_json = json.loads(json_text)
            # --- Added validation ---
            required_keys = {"workflow_summary", "steps", "is_repetitive", "automation_potential"}
            if not isinstance(parsed_json, dict) or not required_keys.issubset(parsed_json.keys()):
                 logger.warning(f"Parsed JSON missing required keys: {parsed_json}")
                 # Try to salvage what's there, but fill defaults
                 parsed_json = {
                     "workflow_summary": parsed_json.get("workflow_summary", "JSON missing keys"),
                     "steps": parsed_json.get("steps", []),
                     "is_repetitive": parsed_json.get("is_repetitive", False),
                     "automation_potential": parsed_json.get("automation_potential", "low")
                 }
            logger.debug("Successfully parsed JSON from LLM response.")
            return parsed_json
        except json.JSONDecodeError as e:
            logger.warning(f"LLM did not return valid JSON. Parse error: {e}. Raw text was: {json_text[:500]}...")
            return {"workflow_summary": "LLM response was not valid JSON.", "steps": [], "is_repetitive": False, "automation_potential": "low"}
