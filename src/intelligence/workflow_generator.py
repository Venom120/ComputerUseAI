from __future__ import annotations

from typing import Any, Dict, List


def generate_automation_plan(workflow_description: Dict[str, Any]) -> List[Dict[str, Any]]:
    steps = []
    for step in workflow_description.get("steps", []):
        action = step.get("action", "")
        target = step.get("target", "")
        steps.append(
            {
                "action_type": action or "noop",
                "target": target,
                "verification": "",
                "retry_count": 2,
                "timeout": 5,
            }
        )
    return steps


