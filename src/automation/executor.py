from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)

from .computer_use import ComputerUse, ComputerUseConfig


@dataclass
class WorkflowStep:
    action_type: str
    target: Any
    verification: str
    retry_count: int = 3
    timeout: int = 5


@dataclass
class ExecutionResult:
    success: bool
    error_message: Optional[str] = None
    execution_time: float = 0.0
    steps_completed: int = 0


class WorkflowExecutor:
    def __init__(self) -> None:
        self.computer_use = ComputerUse(ComputerUseConfig())
        self._running = False

    def load_workflow(self, workflow_path: str | Path) -> List[WorkflowStep]:
        """Load workflow from JSON file"""
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            steps = []
            for step_data in data.get('steps', []):
                step = WorkflowStep(
                    action_type=step_data.get('action_type', 'noop'),
                    target=step_data.get('target', ''),
                    verification=step_data.get('verification', ''),
                    retry_count=step_data.get('retry_count', 3),
                    timeout=step_data.get('timeout', 5)
                )
                steps.append(step)
            
            logger.info("Loaded workflow with %d steps", len(steps))
            return steps
        except Exception as e:
            logger.error("Failed to load workflow: %s", e)
            return []

    def execute_workflow(self, workflow_id: str, steps: List[WorkflowStep], parameters: Dict[str, Any] | None = None) -> ExecutionResult:
        """Execute a workflow with the given steps"""
        if self._running:
            return ExecutionResult(False, "Another workflow is already running")
        
        self._running = True
        start_time = time.time()
        completed_steps = 0
        
        try:
            logger.info("Starting workflow execution: %s", workflow_id)
            
            for i, step in enumerate(steps):
                logger.info("Executing step %d/%d: %s", i + 1, len(steps), step.action_type)
                
                success = self.execute_step(step, parameters or {})
                if not success:
                    error_msg = f"Step {i + 1} failed: {step.action_type}"
                    logger.error(error_msg)
                    return ExecutionResult(
                        False, 
                        error_msg, 
                        time.time() - start_time, 
                        completed_steps
                    )
                
                completed_steps += 1
                time.sleep(0.5)  # Brief pause between steps
            
            execution_time = time.time() - start_time
            logger.info("Workflow completed successfully in %.2fs", execution_time)
            return ExecutionResult(True, None, execution_time, completed_steps)
            
        except Exception as e:
            logger.exception("Workflow execution error: %s", e)
            return ExecutionResult(False, str(e), time.time() - start_time, completed_steps)
        finally:
            self._running = False

    def execute_step(self, step: WorkflowStep, context: Dict[str, Any]) -> bool:
        """Execute a single workflow step with retry logic"""
        for attempt in range(step.retry_count):
            try:
                success = self._execute_action(step, context)
                if success:
                    return True
                
                if attempt < step.retry_count - 1:
                    logger.warning("Step failed, retrying (%d/%d): %s", 
                                 attempt + 1, step.retry_count, step.action_type)
                    time.sleep(1)  # Wait before retry
                
            except Exception as e:
                logger.error("Step execution error (attempt %d): %s", attempt + 1, e)
                if attempt == step.retry_count - 1:
                    return False
        
        return False

    def _execute_action(self, step: WorkflowStep, context: Dict[str, Any]) -> bool:
        """Execute the actual action for a step"""
        action_type = step.action_type.lower()
        
        if action_type == "click":
            if isinstance(step.target, dict) and "x" in step.target and "y" in step.target:
                return self.computer_use.click_at_position(
                    step.target["x"], 
                    step.target["y"]
                )
            return False
        
        elif action_type == "type":
            text = str(step.target)
            return self.computer_use.type_text(text)
        
        elif action_type == "key":
            key = str(step.target)
            return self.computer_use.press_key(key)
        
        elif action_type == "key_combination":
            if isinstance(step.target, list):
                return self.computer_use.press_key_combination(step.target)
            return False
        
        elif action_type == "scroll":
            clicks = int(step.target) if isinstance(step.target, (int, str)) else 3
            return self.computer_use.scroll(clicks)
        
        elif action_type == "wait":
            seconds = float(step.target) if isinstance(step.target, (int, float, str)) else 1.0
            time.sleep(seconds)
            return True
        
        elif action_type == "noop":
            return True
        
        else:
            logger.warning("Unknown action type: %s", action_type)
            return False

    def stop_execution(self) -> None:
        """Stop current workflow execution"""
        self._running = False
        logger.info("Workflow execution stopped")

    def is_running(self) -> bool:
        """Check if a workflow is currently running"""
        return self._running
