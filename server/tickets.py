"""
Support ticket dataset and grading logic for all three tasks.

Task 1 (Easy):   Single unambiguous ticket — correct category/priority/routing.
Task 2 (Medium): Multi-ticket batch — must handle 5 tickets correctly in sequence.
Task 3 (Hard):   Ambiguous / adversarial tickets — edge cases, escalation logic,
                 subtle priority signals, and quality response drafting.
"""

from typing import Any, Dict, List, Optional
import re


# ---------------------------------------------------------------------------
# Ticket definitions
# ---------------------------------------------------------------------------

TASK1_TICKET = {
    "ticket_id": "TKT-001",
    "subject": "Charged twice for my subscription",
    "body": (
        "Hello, I was charged $29.99 twice this month for my subscription. "
        "My order number is #ORD-88821. Please refund the duplicate charge immediately. "
        "This is very frustrating as it's caused my bank account to go negative."
    ),
    "customer_tier": "standard",
    "previous_tickets": 1,
    "account_age_days": 180,
    # Ground truth
    "gt_category": "billing",
    "gt_priority": "high",
    "gt_team": "billing_team",
    "gt_escalation": False,
}

TASK2_TICKETS = [
    {
        "ticket_id": "TKT-101",
        "subject": "Cannot login to my account",
        "body": (
            "I've been locked out of my account for 2 days. "
            "I tried resetting my password but never received the email. "
            "I need access urgently for a work deadline tomorrow."
        ),
        "customer_tier": "premium",
        "previous_tickets": 0,
        "account_age_days": 365,
        "gt_category": "account",
        "gt_priority": "high",
        "gt_team": "account_team",
        "gt_escalation": False,
    },
    {
        "ticket_id": "TKT-102",
        "subject": "Where is my order?",
        "body": (
            "I ordered 3 weeks ago and still nothing has arrived. "
            "Order #ORD-55512. Tracking shows it's been stuck in the warehouse for 2 weeks."
        ),
        "customer_tier": "standard",
        "previous_tickets": 2,
        "account_age_days": 400,
        "gt_category": "shipping",
        "gt_priority": "high",
        "gt_team": "fulfillment",
        "gt_escalation": False,
    },
    {
        "ticket_id": "TKT-103",
        "subject": "Question about pricing plans",
        "body": (
            "Hi, I'm considering upgrading to the premium plan. "
            "Can you tell me what the differences are between Standard and Premium? "
            "Specifically around storage limits and API access."
        ),
        "customer_tier": "standard",
        "previous_tickets": 0,
        "account_age_days": 30,
        "gt_category": "general",
        "gt_priority": "low",
        "gt_team": "general_support",
        "gt_escalation": False,
    },
    {
        "ticket_id": "TKT-104",
        "subject": "App crashes on startup after update",
        "body": (
            "After the latest update (v2.4.1) the app immediately crashes on launch. "
            "I'm on iPhone 14, iOS 17.2. I've tried reinstalling but same issue. "
            "This is preventing me from doing my job."
        ),
        "customer_tier": "premium",
        "previous_tickets": 3,
        "account_age_days": 730,
        "gt_category": "technical",
        "gt_priority": "high",
        "gt_team": "tech_support",
        "gt_escalation": False,
    },
    {
        "ticket_id": "TKT-105",
        "subject": "I want to return my purchase",
        "body": (
            "I bought the annual plan last week but I've decided it's not for me. "
            "I would like a full refund under your 30-day money back guarantee. "
            "Order #ORD-77234."
        ),
        "customer_tier": "standard",
        "previous_tickets": 0,
        "account_age_days": 7,
        "gt_category": "returns",
        "gt_priority": "medium",
        "gt_team": "returns_team",
        "gt_escalation": False,
    },
]

TASK3_TICKETS = [
    {
        "ticket_id": "TKT-201",
        "subject": "URGENT: Production system completely down",
        "body": (
            "Our entire production environment has been down for 45 minutes due to an API error "
            "from your service. We're losing $10,000/minute. We have 50,000 end users affected. "
            "I've already spoken to two of your agents who couldn't help. "
            "I need your CTO on the phone NOW. This is unacceptable."
        ),
        "customer_tier": "enterprise",
        "previous_tickets": 12,
        "account_age_days": 1825,
        "gt_category": "technical",
        "gt_priority": "critical",
        "gt_team": "tech_support",
        "gt_escalation": True,  # Must escalate
    },
    {
        "ticket_id": "TKT-202",
        "subject": "Billing question",
        "body": (
            "Hi there. I noticed a charge of $0.50 on my statement that I don't recognize. "
            "It might be a currency conversion fee but I'm not sure. No rush, "
            "just want to understand what it's for when you get a chance. Thanks!"
        ),
        "customer_tier": "standard",
        "previous_tickets": 0,
        "account_age_days": 90,
        "gt_category": "billing",
        "gt_priority": "low",   # Low despite 'billing' — tiny amount, no urgency
        "gt_team": "billing_team",
        "gt_escalation": False,
    },
    {
        "ticket_id": "TKT-203",
        "subject": "My account was hacked",
        "body": (
            "Someone has accessed my account without my permission. "
            "I can see login activity from Russia at 3am when I was asleep. "
            "They changed my email address so I can no longer log in. "
            "I have important business data in there. Please help immediately."
        ),
        "customer_tier": "premium",
        "previous_tickets": 1,
        "account_age_days": 500,
        "gt_category": "account",
        "gt_priority": "critical",  # Security breach = critical
        "gt_team": "account_team",
        "gt_escalation": True,  # Security incident must escalate
    },
    {
        "ticket_id": "TKT-204",
        "subject": "Feature request: dark mode",
        "body": (
            "I love the product! One thing I'd really appreciate is a dark mode option. "
            "Many other products have it and I find it much easier on my eyes at night. "
            "Would this be on your roadmap? Thanks for the great work!"
        ),
        "customer_tier": "standard",
        "previous_tickets": 0,
        "account_age_days": 200,
        "gt_category": "general",
        "gt_priority": "low",
        "gt_team": "general_support",
        "gt_escalation": False,
        "gt_needs_more_info": False,
    },
    {
        "ticket_id": "TKT-205",
        "subject": "Invoice discrepancy",
        "body": (
            "The invoice for our enterprise contract (INV-2024-0892) shows $45,000 "
            "but our signed contract states $38,500 for the same service tier. "
            "We cannot process payment until this is resolved. "
            "Our finance team has flagged this for legal review if not corrected by Friday."
        ),
        "customer_tier": "enterprise",
        "previous_tickets": 5,
        "account_age_days": 900,
        "gt_category": "billing",
        "gt_priority": "critical",  # Contract dispute, legal threat
        "gt_team": "billing_team",
        "gt_escalation": True,
    },
]


# ---------------------------------------------------------------------------
# Grading helpers
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {"billing", "technical", "account", "shipping", "returns", "general"}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
VALID_TEAMS = {
    "billing_team", "tech_support", "account_team",
    "fulfillment", "returns_team", "general_support",
}

PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

# Correct category → correct team mapping
CATEGORY_TEAM_MAP = {
    "billing": "billing_team",
    "technical": "tech_support",
    "account": "account_team",
    "shipping": "fulfillment",
    "returns": "returns_team",
    "general": "general_support",
}


def _response_quality(draft: str, ticket: Dict) -> float:
    """Score response draft quality 0.0–1.0."""
    if not draft or len(draft.strip()) < 20:
        return 0.0

    score = 0.0
    draft_lower = draft.lower()
    ticket_body_lower = ticket["body"].lower()

    # Has a greeting
    if any(g in draft_lower for g in ["hello", "hi ", "dear", "greetings", "thank"]):
        score += 0.2

    # Acknowledges the issue
    words_in_body = set(re.findall(r'\w+', ticket_body_lower))
    words_in_draft = set(re.findall(r'\w+', draft_lower))
    overlap = len(words_in_body & words_in_draft) / max(len(words_in_body), 1)
    score += min(overlap * 2, 0.3)

    # Has a closing
    if any(c in draft_lower for c in ["regards", "sincerely", "team", "support", "help you"]):
        score += 0.2

    # Reasonable length (50–400 chars is good)
    length = len(draft.strip())
    if 50 <= length <= 400:
        score += 0.3
    elif length > 400:
        score += 0.15  # Too long
    elif length > 20:
        score += 0.1   # Too short

    return min(score, 1.0)


def grade_single_ticket(action: Dict, ticket: Dict) -> Dict[str, Any]:
    """
    Grade one triage action against one ticket ground truth.
    Returns a dict with component scores and overall reward (0.0–1.0).
    """
    results = {}

    # --- Category (25 pts) ---
    cat = (action.get("category") or "").strip().lower()
    gt_cat = ticket["gt_category"]
    cat_correct = cat == gt_cat
    results["category_correct"] = cat_correct
    results["category_score"] = 1.0 if cat_correct else 0.0

    # --- Priority (25 pts) ---
    pri = (action.get("priority") or "").strip().lower()
    gt_pri = ticket["gt_priority"]
    pri_correct = pri == gt_pri
    # Partial credit for being one level off
    if pri_correct:
        pri_score = 1.0
    elif pri in PRIORITY_ORDER and gt_pri in PRIORITY_ORDER:
        diff = abs(PRIORITY_ORDER[pri] - PRIORITY_ORDER[gt_pri])
        pri_score = max(0.0, 1.0 - diff * 0.5)
    else:
        pri_score = 0.0
    results["priority_correct"] = pri_correct
    results["priority_score"] = pri_score

    # --- Team routing (25 pts) ---
    team = (action.get("team") or "").strip().lower()
    gt_team = ticket["gt_team"]
    team_correct = team == gt_team
    # Partial: if category was right, team follows — reward category-team consistency
    if team_correct:
        team_score = 1.0
    elif cat_correct and team == CATEGORY_TEAM_MAP.get(cat, ""):
        team_score = 1.0  # Correct team for correct category
    elif team in VALID_TEAMS:
        team_score = 0.1  # Valid but wrong
    else:
        team_score = 0.0
    results["team_correct"] = team_correct
    results["team_score"] = team_score

    # --- Escalation (15 pts) ---
    escalate = bool(action.get("needs_escalation", False))
    gt_escalate = ticket.get("gt_escalation", False)
    esc_correct = escalate == gt_escalate
    if esc_correct:
        esc_score = 1.0
    elif gt_escalate and not escalate:
        esc_score = 0.0  # Missed critical escalation
    else:
        esc_score = 0.5  # Over-escalated (minor error)
    results["escalation_correct"] = esc_correct
    results["escalation_score"] = esc_score

    # --- Response draft quality (10 pts) ---
    draft = action.get("response_draft", "")
    draft_score = _response_quality(draft, ticket)
    results["response_score"] = draft_score

    # --- Weighted total ---
    total = (
        results["category_score"]  * 0.25 +
        results["priority_score"]  * 0.25 +
        results["team_score"]      * 0.25 +
        results["escalation_score"]* 0.15 +
        results["response_score"]  * 0.10
    )
    results["reward"] = round(total, 4)
    results["feedback"] = _build_feedback(results, action, ticket)

    return results


def _build_feedback(results: Dict, action: Dict, ticket: Dict) -> str:
    """Build human-readable feedback string."""
    parts = []
    cat = (action.get("category") or "").lower()
    pri = (action.get("priority") or "").lower()
    team = (action.get("team") or "").lower()

    if results["category_correct"]:
        parts.append(f"✓ Category '{cat}' correct")
    else:
        parts.append(f"✗ Category '{cat}' wrong (expected '{ticket['gt_category']}')")

    if results["priority_correct"]:
        parts.append(f"✓ Priority '{pri}' correct")
    else:
        parts.append(f"✗ Priority '{pri}' wrong (expected '{ticket['gt_priority']}')")

    if results["team_correct"]:
        parts.append(f"✓ Team '{team}' correct")
    else:
        parts.append(f"✗ Team '{team}' wrong (expected '{ticket['gt_team']}')")

    esc = bool(action.get("needs_escalation", False))
    gt_esc = ticket.get("gt_escalation", False)
    if esc == gt_esc:
        parts.append(f"✓ Escalation={esc} correct")
    else:
        parts.append(f"✗ Escalation={esc} wrong (expected {gt_esc})")

    rs = results["response_score"]
    parts.append(f"Response quality: {rs:.0%}")

    return " | ".join(parts)
