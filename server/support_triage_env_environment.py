"""
Support Ticket Triage Environment — stateless HTTP implementation.

Because the OpenEnv HTTP server creates a fresh env per request,
we make the environment fully stateless: the action carries task_name
and ticket_index, and the env grades exactly that ticket.
"""

import sys, os
_env_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _env_root not in sys.path:
    sys.path.insert(0, _env_root)

import uuid
from typing import Optional
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from models import TriageAction, TicketObservation
from server.tickets import (
    TASK1_TICKET, TASK2_TICKETS, TASK3_TICKETS,
    grade_single_ticket, VALID_CATEGORIES, VALID_PRIORITIES, VALID_TEAMS,
)

TASKS = {
    "easy_single_ticket": {
        "description": (
            "Triage one unambiguous support ticket. "
            "Correctly classify category, set priority, route to the right team, "
            "set escalation flag, and draft an initial customer response."
        ),
        "tickets": [TASK1_TICKET],
        "hints": [
            "Duplicate charges are always 'high' priority",
            "Billing issues always route to billing_team",
            "Write a professional empathetic response",
        ],
    },
    "medium_batch_triage": {
        "description": (
            "Triage a batch of 5 diverse support tickets. "
            "Submit one action per ticket using ticket_index 0-4."
        ),
        "tickets": TASK2_TICKETS,
        "hints": [
            "Each ticket belongs to a different category",
            "Premium customers with urgent issues get 'high' priority",
            "A simple pricing question is 'low' priority",
            "Match category to team exactly",
        ],
    },
    "hard_adversarial_triage": {
        "description": (
            "Triage 5 difficult tickets with ambiguous signals. "
            "Correctly identify critical priorities and escalation requirements."
        ),
        "tickets": TASK3_TICKETS,
        "hints": [
            "Enterprise production outages are ALWAYS critical + escalate",
            "Account hacking is critical + escalate",
            "A $0.50 charge with 'no rush' is low priority",
            "Contract disputes with legal threats need escalation",
        ],
    },
}


class SupportTriageEnvironment(Environment):
    """
    Stateless support ticket triage environment.
    Each step grades exactly the ticket specified by (task_name, ticket_index).
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid.uuid4()), step_count=0)
        self._last_task = "easy_single_ticket"
        self._last_index = 0

    def reset(self, task: Optional[str] = None, **kwargs) -> TicketObservation:
        task_name = task or "easy_single_ticket"
        if task_name not in TASKS:
            task_name = "easy_single_ticket"
        self._last_task = task_name
        self._last_index = 0
        self._state = State(episode_id=str(uuid.uuid4()), step_count=0)
        return self._make_obs(task_name, 0, reward=0.0, done=False, feedback=None)

    def step(self, action: TriageAction) -> TicketObservation:  # type: ignore[override]
        task_name = (action.task_name or self._last_task or "easy_single_ticket")
        if task_name not in TASKS:
            task_name = "easy_single_ticket"

        tickets = TASKS[task_name]["tickets"]
        idx = max(0, min(action.ticket_index, len(tickets) - 1))

        self._last_task = task_name
        self._last_index = idx
        self._state.step_count += 1

        errors = self._validate(action)
        if errors:
            reward = 0.0
            feedback = "Invalid: " + "; ".join(errors)
        else:
            result = grade_single_ticket({
                "category": action.category,
                "priority": action.priority,
                "team": action.team,
                "response_draft": action.response_draft,
                "needs_escalation": action.needs_escalation,
                "needs_more_info": action.needs_more_info,
            }, tickets[idx])
            reward = result["reward"]
            feedback = result["feedback"]

        # Done when this is the last ticket in the task
        done = (idx >= len(tickets) - 1)
        next_idx = idx + 1 if not done else idx

        return self._make_obs(task_name, next_idx, reward=reward, done=done, feedback=feedback)

    @property
    def state(self) -> State:
        return self._state

    def _make_obs(self, task_name, ticket_idx, reward, done, feedback):
        task_cfg = TASKS[task_name]
        tickets = task_cfg["tickets"]
        show_idx = min(ticket_idx, len(tickets) - 1)
        ticket = tickets[show_idx]

        return TicketObservation(
            ticket_id=ticket["ticket_id"],
            subject=ticket["subject"],
            body=ticket["body"],
            customer_tier=ticket.get("customer_tier", "standard"),
            previous_tickets=ticket.get("previous_tickets", 0),
            account_age_days=ticket.get("account_age_days", 0),
            task_name=task_name,
            task_description=task_cfg["description"],
            step_number=ticket_idx,
            max_steps=len(tickets),
            last_action_result=feedback,
            grader_hints=task_cfg["hints"],
            done=done,
            reward=reward,
            metadata={
                "episode_id": self._state.episode_id,
                "next_ticket_index": ticket_idx,
            },
        )

    def _validate(self, action):
        errors = []
        if (action.category or "").lower() not in VALID_CATEGORIES:
            errors.append(f"category '{action.category}' invalid")
        if (action.priority or "").lower() not in VALID_PRIORITIES:
            errors.append(f"priority '{action.priority}' invalid")
        if (action.team or "").lower() not in VALID_TEAMS:
            errors.append(f"team '{action.team}' invalid")
        if len(action.response_draft) > 500:
            errors.append("response_draft too long (max 500 chars)")
        return errors