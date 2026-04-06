"""
Data models for the Support Ticket Triage Environment.
"""

from typing import Any, Dict, List, Optional
from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class TriageAction(Action):
    """
    Action the agent takes on a support ticket.
    Includes task_name so the stateless HTTP server knows which task to run.
    """

    task_name: str = Field(
        default="easy_single_ticket",
        description=(
            "Task to run. One of: 'easy_single_ticket', "
            "'medium_batch_triage', 'hard_adversarial_triage'"
        ),
    )
    ticket_index: int = Field(
        default=0,
        description="Which ticket in the task to grade (0-based index)",
    )
    category: str = Field(
        ...,
        description=(
            "Issue category. Must be one of: "
            "'billing', 'technical', 'account', 'shipping', 'returns', 'general'"
        ),
    )
    priority: str = Field(
        ...,
        description="Priority level. Must be one of: 'critical', 'high', 'medium', 'low'",
    )
    team: str = Field(
        ...,
        description=(
            "Routing destination. Must be one of: "
            "'billing_team', 'tech_support', 'account_team', "
            "'fulfillment', 'returns_team', 'general_support'"
        ),
    )
    response_draft: str = Field(
        default="",
        description="Optional initial response draft to send to the customer (0-500 chars)",
    )
    needs_escalation: bool = Field(
        default=False,
        description="Whether this ticket needs escalation to a senior agent or manager",
    )
    needs_more_info: bool = Field(
        default=False,
        description="Whether the agent should request more information from the customer",
    )


class TicketObservation(Observation):
    """Observation presented to the agent: a support ticket to triage."""

    ticket_id: str = Field(..., description="Unique ticket identifier")
    subject: str = Field(..., description="Ticket subject line")
    body: str = Field(..., description="Full ticket body text")
    customer_tier: str = Field(
        default="standard",
        description="Customer tier: 'standard', 'premium', or 'enterprise'",
    )
    previous_tickets: int = Field(default=0)
    account_age_days: int = Field(default=0)
    task_name: str = Field(default="")
    task_description: str = Field(default="")
    step_number: int = Field(default=0)
    max_steps: int = Field(default=1)
    last_action_result: Optional[str] = Field(default=None)
    grader_hints: List[str] = Field(default_factory=list)