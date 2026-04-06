---
title: Support Ticket Triage Environment
emoji: 🎫
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
tags:
  - openenv
  - rl
  - agent-evaluation
  - customer-support
  - nlp
---

# Support Ticket Triage — OpenEnv Environment

An OpenEnv environment where AI agents learn to triage customer support tickets. The agent reads incoming tickets and must classify the issue, set the right priority, route it to the correct team, decide whether it needs escalation, and draft an initial response to the customer.

This is a genuine operational task that support teams at large companies perform thousands of times every day. We built it as an OpenEnv environment so that AI agents can be trained and evaluated against it in a reproducible, measurable way.

---

## Why this environment?

Support ticket triage is a good benchmark for agents because it requires several things at once — reading comprehension, following rules, making judgment calls under ambiguity, and producing a useful output. It is also easy to grade: each ticket has a correct category, a correct priority level, and a correct team to route to. This means we can give agents precise, deterministic feedback on every decision they make.

The task also has natural difficulty levels. Some tickets are obvious. Others have misleading signals — a ticket that looks like a billing issue might actually be a security incident, or a ticket from an enterprise customer might need escalation even if the language sounds calm.

---

## Action and Observation Spaces

### What the agent does — TriageAction

| Field | Type | Values |
|-------|------|--------|
| `category` | str | `billing`, `technical`, `account`, `shipping`, `returns`, `general` |
| `priority` | str | `critical`, `high`, `medium`, `low` |
| `team` | str | `billing_team`, `tech_support`, `account_team`, `fulfillment`, `returns_team`, `general_support` |
| `response_draft` | str | A customer-facing response, up to 500 characters |
| `needs_escalation` | bool | Whether a senior agent or manager needs to see this |
| `needs_more_info` | bool | Whether the agent should ask the customer for more details |

### What the agent sees — TicketObservation

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | str | Unique ticket ID |
| `subject` | str | Ticket subject line |
| `body` | str | Full ticket body |
| `customer_tier` | str | `standard`, `premium`, or `enterprise` |
| `previous_tickets` | int | How many tickets this customer has submitted before |
| `account_age_days` | int | How old the customer account is |
| `task_name` | str | Which task is currently running |
| `task_description` | str | Description of what the agent needs to do |
| `step_number` | int | Which step in the episode this is |
| `max_steps` | int | Total number of steps in the episode |
| `last_action_result` | str | Feedback from the previous step |
| `grader_hints` | list | Hints about what the grader is looking for |

---

## Tasks

### Task 1 — easy_single_ticket

One straightforward billing ticket. The agent needs to correctly classify it, set the priority, route it, and write a short response. There is no ambiguity here — it is designed to verify that the agent can handle the basics.

- Steps: 1
- Expected score for capable models: 0.85 to 1.0

### Task 2 — medium_batch_triage

Five tickets in sequence, each from a different category: an account lockout, a shipping delay, a pricing question, an app crash, and a refund request. The agent processes them one by one. The challenge is that each ticket requires different reasoning — what makes a shipping ticket high priority is different from what makes a technical ticket high priority.

- Steps: 5
- Expected score for capable models: 0.70 to 0.90

### Task 3 — hard_adversarial_triage

Five tickets designed to be difficult. They include an enterprise production outage, a minor billing question that looks urgent but is not, a hacked account, a feature request, and a contract dispute with a legal threat. The agent must correctly identify which ones are critical and which ones need escalation. Surface-level signals are often misleading.

- Steps: 5
- Expected score for capable models: 0.50 to 0.85

---

## Reward Function

Each ticket is graded across five components:

| Component | Weight | How it is scored |
|-----------|--------|-----------------|
| Category | 25% | Full credit if correct, none if wrong |
| Priority | 25% | Full credit if correct, half credit if one level off, none if two or more levels off |
| Team routing | 25% | Full credit if correct |
| Escalation | 15% | Full credit if correct, no credit for missing a required escalation, half credit for escalating unnecessarily |
| Response draft | 10% | Scored on greeting, issue acknowledgement, professional closing, and appropriate length |

The episode score is the average reward across all steps, normalized to a range of 0.0 to 1.0. Agents get a reward signal after every single step, not just at the end — this makes it easier for models to learn from their mistakes incrementally.

---

## Baseline Scores

Measured with Qwen/Qwen2.5-72B-Instruct via the HuggingFace router:

| Task | Score | Notes |
|------|-------|-------|
| easy_single_ticket | 0.985 | Near-perfect on the clear-cut ticket |
| medium_batch_triage | 0.884 | Small error on the pricing question priority |
| hard_adversarial_triage | 0.980 | Handled escalation and critical priorities well |

---

## Setup and Usage

### Run locally

```bash
git clone https://huggingface.co/spaces/zenertrizz/support-triage-env
cd support-triage-env
pip install "openenv-core[core]>=0.2.2" uvicorn
export PYTHONPATH=$(pwd)
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Run with Docker

```bash
docker build -t support-triage-env .
docker run -p 7860:7860 support-triage-env
```

### Validate

```bash
pip install openenv-core
openenv validate .
```

### Run the inference baseline

```bash
export HF_TOKEN=your_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export ENV_BASE_URL=http://localhost:7860
python inference.py
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reset` | Start a new episode. Pass `{"task": "easy_single_ticket"}` in the body |
| POST | `/step` | Submit a triage action |
| GET | `/state` | Get the current episode state |
| GET | `/schema` | Get the action and observation schemas |
| GET | `/health` | Health check |
| WS | `/ws` | WebSocket endpoint for persistent sessions |

---

## Project Structure

```
support-triage-env/
├── openenv.yaml
├── pyproject.toml
├── uv.lock
├── models.py
├── client.py
├── inference.py
├── Dockerfile
├── README.md
└── server/
    ├── app.py
    ├── support_triage_env_environment.py
    ├── tickets.py
    └── Dockerfile
```