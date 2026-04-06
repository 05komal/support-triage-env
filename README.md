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

# 🎫 Support Ticket Triage — OpenEnv Environment

An OpenEnv environment where AI agents learn to **triage customer support tickets**: classify issues, set priorities, route to the right team, decide when to escalate, and draft initial responses.

This models a genuine operational task run thousands of times daily by support teams worldwide.

---

## 🌍 Why This Environment?

Support ticket triage is:
- **High-volume** — large companies handle 10,000s of tickets/day
- **Consequential** — wrong priority → SLA breach or churned customer
- **Multi-dimensional** — agents must reason across category, urgency, routing, and communication
- **Measurable** — ground-truth labels enable deterministic grading

It's an ideal testbed for agents that must follow instructions, read context carefully, and make nuanced judgment calls.

---

## 📐 Action & Observation Spaces

### Action: `TriageAction`
| Field | Type | Values |
|-------|------|--------|
| `category` | str | `billing`, `technical`, `account`, `shipping`, `returns`, `general` |
| `priority` | str | `critical`, `high`, `medium`, `low` |
| `team` | str | `billing_team`, `tech_support`, `account_team`, `fulfillment`, `returns_team`, `general_support` |
| `response_draft` | str | 0–500 char customer-facing response |
| `needs_escalation` | bool | True if ticket needs senior agent/manager |
| `needs_more_info` | bool | True if agent should request more info |

### Observation: `TicketObservation`
| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | str | Unique ticket ID |
| `subject` | str | Ticket subject line |
| `body` | str | Full ticket body |
| `customer_tier` | str | `standard`, `premium`, or `enterprise` |
| `previous_tickets` | int | Customer's ticket history count |
| `account_age_days` | int | Account age signal |
| `task_name` | str | Current task identifier |
| `task_description` | str | What the agent must accomplish |
| `step_number` | int | Current step in episode |
| `max_steps` | int | Total steps in episode |
| `last_action_result` | str | Feedback from previous step |
| `grader_hints` | list[str] | Hints about grading criteria |

---

## 🎯 Tasks

### Task 1 — `easy_single_ticket` ⭐
One clear-cut billing ticket. Tests basic classification, priority-setting, and routing.

- **Steps:** 1
- **Expected score:** ~0.85–1.0 for capable models
- **Key challenge:** Correct category + team + writing a decent response draft

### Task 2 — `medium_batch_triage` ⭐⭐
Five tickets of different categories in sequence: account lockout, shipping delay, pricing question, app crash, and a return request.

- **Steps:** 5
- **Expected score:** ~0.70–0.90 for capable models
- **Key challenge:** Different priority logic per ticket type; premium vs standard tier signals

### Task 3 — `hard_adversarial_triage` ⭐⭐⭐
Five difficult tickets with subtle signals: enterprise production outage, low-stakes billing question, account security breach, feature request, and a contract dispute with legal threat.

- **Steps:** 5
- **Expected score:** ~0.50–0.85 for frontier models
- **Key challenge:** Correctly identifying `critical` priority and escalation requirements; distinguishing similar surface forms with different urgency

---

## 📊 Reward Function

Each ticket is graded on 5 components, weighted as:

| Component | Weight | Scoring |
|-----------|--------|---------|
| Category | 25% | 1.0 if correct, 0.0 if wrong |
| Priority | 25% | 1.0 if correct, 0.5 if 1 level off, 0.0 if 2+ levels off |
| Team routing | 25% | 1.0 if correct; also 1.0 if team matches correct category |
| Escalation | 15% | 1.0 if correct; 0.0 for missed escalations; 0.5 for over-escalation |
| Response draft | 10% | Quality score 0–1 based on greeting, issue acknowledgement, professional closing, and length |

Episode score = mean reward across all steps (normalized to [0, 1]).

The reward is **dense** — agents receive signal every step, not just at episode end. Partial credit on priority (one level off) prevents sparse learning in the priority dimension.

---

## 🚀 Setup & Usage

### Quick start (local)
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/support-triage-env
cd support-triage-env
pip install "openenv-core[core]>=0.2.2"
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker build -t support-triage-env -f server/Dockerfile .
docker run -p 8000:8000 support-triage-env
```

### Validate
```bash
openenv validate .
```

### Run inference baseline
```bash
export HF_TOKEN=your_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export ENV_BASE_URL=http://localhost:8000
python inference.py
```

---

## 📈 Baseline Scores

Measured with `Qwen/Qwen2.5-72B-Instruct` via HuggingFace router:

| Task | Score | Notes |
|------|-------|-------|
| `easy_single_ticket` | ~0.92 | Near-perfect on clear-cut ticket |
| `medium_batch_triage` | ~0.82 | Occasional priority misjudgement |
| `hard_adversarial_triage` | ~0.68 | Struggles with escalation on subtle tickets |

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reset` | Start new episode. Body: `{"task": "easy_single_ticket"}` |
| POST | `/step` | Submit triage action |
| GET | `/state` | Current episode state |
| GET | `/schema` | Action/observation schemas |
| GET | `/health` | Health check |
| WS | `/ws` | WebSocket for persistent sessions |

---

## 📁 Project Structure
```
support-triage-env/
├── openenv.yaml              # OpenEnv spec
├── pyproject.toml            # Package config + uv.lock
├── models.py                 # TriageAction + TicketObservation
├── client.py                 # EnvClient implementation
├── inference.py              # Baseline inference script
├── server/
│   ├── app.py                # FastAPI app
│   ├── support_triage_env_environment.py  # Environment logic
│   ├── tickets.py            # Ticket dataset + graders
│   └── Dockerfile
└── README.md
```
