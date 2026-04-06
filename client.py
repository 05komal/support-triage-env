"""Support Ticket Triage Environment Client."""
from typing import Dict
from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import TriageAction, TicketObservation
except ImportError:
    from models import TriageAction, TicketObservation


class SupportTriageEnv(EnvClient[TriageAction, TicketObservation, State]):
    """Client for the Support Ticket Triage Environment."""

    def _step_payload(self, action: TriageAction) -> Dict:
        return {
            "category": action.category,
            "priority": action.priority,
            "team": action.team,
            "response_draft": action.response_draft,
            "needs_escalation": action.needs_escalation,
            "needs_more_info": action.needs_more_info,
        }

    def _parse_result(self, payload: Dict) -> StepResult[TicketObservation]:
        obs_data = payload.get("observation", {})
        observation = TicketObservation(
            ticket_id=obs_data.get("ticket_id", ""),
            subject=obs_data.get("subject", ""),
            body=obs_data.get("body", ""),
            customer_tier=obs_data.get("customer_tier", "standard"),
            previous_tickets=obs_data.get("previous_tickets", 0),
            account_age_days=obs_data.get("account_age_days", 0),
            task_name=obs_data.get("task_name", ""),
            task_description=obs_data.get("task_description", ""),
            step_number=obs_data.get("step_number", 0),
            max_steps=obs_data.get("max_steps", 1),
            last_action_result=obs_data.get("last_action_result"),
            grader_hints=obs_data.get("grader_hints", []),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
            metadata=obs_data.get("metadata", {}),
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
