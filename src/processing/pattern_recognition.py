from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def extract_workflow_signature(workflow: Dict[str, Any]) -> str:
    app = workflow.get("application", "")
    actions = " ".join(step.get("action", "") for step in workflow.get("steps", []))
    text = workflow.get("workflow_summary", "")
    return f"{app} | {actions} | {text}"


def calculate_similarity(workflow1: Dict[str, Any], workflow2: Dict[str, Any]) -> float:
    vec = TfidfVectorizer().fit([
        extract_workflow_signature(workflow1),
        extract_workflow_signature(workflow2),
    ])
    a = vec.transform([extract_workflow_signature(workflow1)])
    b = vec.transform([extract_workflow_signature(workflow2)])
    sim = cosine_similarity(a, b)[0][0]
    return float(sim)


def detect_repetitive_patterns(workflows: List[Dict[str, Any]], threshold: float = 0.85) -> List[Dict[str, Any]]:
    patterns: List[Dict[str, Any]] = []
    used = set()
    for i in range(len(workflows)):
        if i in used:
            continue
        group = [workflows[i]]
        used.add(i)
        for j in range(i + 1, len(workflows)):
            if j in used:
                continue
            if calculate_similarity(workflows[i], workflows[j]) >= threshold:
                group.append(workflows[j])
                used.add(j)
        if len(group) >= 3:
            patterns.append(
                {
                    "pattern_id": f"pattern_{i}",
                    "occurrences": len(group),
                    "workflow_template": group[0],
                    "confidence": 0.9,
                    "suggested_automation": "Auto-execute common steps",
                }
            )
    return patterns


