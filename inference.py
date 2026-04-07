"""
Inference Script — Support Ticket Triage Environment
=====================================================
Runs an LLM agent against all three tasks.

MANDATORY ENV VARS:
    HF_TOKEN       API key for HuggingFace
    API_BASE_URL   LLM endpoint (default: HuggingFace router)
    MODEL_NAME     Model identifier
    ENV_BASE_URL   Environment server URL (default: http://localhost:8000)

STDOUT FORMAT:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...>
"""

import json, os, sys, textwrap, urllib.request, urllib.error
from typing import Dict, List, Optional
from openai import OpenAI

# ── Config ───────────────────────────────────────────────────────────────────
# NOTE: API_KEY and API_BASE_URL are read inside main() via os.environ[] directly
MODEL_NAME       = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN         = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
ENV_BASE_URL     = os.getenv("ENV_BASE_URL", "http://localhost:8000").rstrip("/")
BENCHMARK    = "support_triage_env"
SUCCESS_THRESHOLD = 0.5

# Task definitions: name → list of ticket indices to process
TASKS = {
    "easy_single_ticket":    {"tickets": 1},
    "medium_batch_triage":   {"tickets": 5},
    "hard_adversarial_triage": {"tickets": 5},
}

# ── Logging ──────────────────────────────────────────────────────────────────
def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    err = error if error else "null"
    action_safe = str(action).replace("\n", " ")[:200]
    print(f"[STEP] step={step} action={action_safe} reward={reward:.2f} done={str(done).lower()} error={err}", flush=True)

def log_end(success, steps, score, rewards):
    r = ",".join(f"{x:.2f}" for x in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={r}", flush=True)

# ── HTTP helpers ──────────────────────────────────────────────────────────────
def http_post(url, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def http_get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode())

# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = textwrap.dedent("""
You are an expert customer support manager triaging support tickets.
Respond ONLY with a valid JSON object — no explanation, no markdown fences.

Required fields:
{
  "category": "<billing|technical|account|shipping|returns|general>",
  "priority": "<critical|high|medium|low>",
  "team": "<billing_team|tech_support|account_team|fulfillment|returns_team|general_support>",
  "response_draft": "<50-300 char professional response to the customer>",
  "needs_escalation": <true|false>,
  "needs_more_info": <false>
}

Priority rules:
- critical: production outages, security breaches, legal threats, enterprise emergencies
- high: account lockouts, duplicate charges, app crashes affecting work, long shipping delays
- medium: returns, moderate delays, non-urgent billing questions
- low: feature requests, general inquiries, minor questions

Team routing (must match category):
billing→billing_team, technical→tech_support, account→account_team,
shipping→fulfillment, returns→returns_team, general→general_support

Escalate when: enterprise outage, security breach, legal threat, critical priority issue.
""").strip()

def build_prompt(obs, step, total):
    hints = "\n".join(f"  - {h}" for h in obs.get("grader_hints", []))
    return textwrap.dedent(f"""
    Task: {obs.get('task_name','')} | Ticket {step} of {total}
    Customer Tier: {obs.get('customer_tier','standard')} | 
    Account age: {obs.get('account_age_days',0)} days | 
    Previous tickets: {obs.get('previous_tickets',0)}

    Subject: {obs.get('subject','')}
    {obs.get('body','')}

    Hints:
{hints}

    Respond with JSON only.
    """).strip()

def call_model(client, obs, step, total):
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": build_prompt(obs, step, total)},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
        # Strip markdown fences if present
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except json.JSONDecodeError:
        print(f"[DEBUG] JSON parse failed, using fallback", flush=True)
    except Exception as e:
        print(f"[DEBUG] Model call failed: {e}", flush=True)
    # Safe fallback
    return {
        "category": "general", "priority": "medium", "team": "general_support",
        "response_draft": "Thank you for contacting us. We will look into this shortly.",
        "needs_escalation": False, "needs_more_info": False,
    }

# ── Episode runner ────────────────────────────────────────────────────────────
def run_task(client, task_name):
    n_tickets = TASKS[task_name]["tickets"]
    rewards, steps_taken = [], 0
    score, success = 0.0, False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset to get first ticket observation
        result = http_post(f"{ENV_BASE_URL}/reset", {"task": task_name})
        obs = result.get("observation", result)

        for step in range(1, n_tickets + 1):
            ticket_index = step - 1

            # Ask LLM to triage this ticket
            action_dict = call_model(client, obs, step, n_tickets)

            # Add routing fields needed by stateless env
            action_dict["task_name"]    = task_name
            action_dict["ticket_index"] = ticket_index

            # Step the environment
            step_result = http_post(f"{ENV_BASE_URL}/step", {"action": action_dict})
            reward  = float(step_result.get("reward", 0.0))
            done    = bool(step_result.get("done", False))
            obs     = step_result.get("observation", step_result)
            err_msg = step_result.get("error")

            action_log = (
                f"cat={action_dict.get('category','')},"
                f"pri={action_dict.get('priority','')},"
                f"team={action_dict.get('team','')},"
                f"esc={action_dict.get('needs_escalation',False)}"
            )
            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action_log, reward=reward, done=done, error=err_msg)

        score   = min(max(sum(rewards) / max(len(rewards), 1), 0.0), 1.0)
        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Task {task_name} failed: {e}", flush=True)
        score   = sum(rewards) / max(len(rewards), 1) if rewards else 0.0
        success = False
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


def main():
    client = OpenAI(
        api_key=os.environ["API_KEY"],
        base_url=os.environ["API_BASE_URL"],
    )

    try:
        http_get(f"{ENV_BASE_URL}/health")
        print(f"[DEBUG] Server at {ENV_BASE_URL} is healthy", flush=True)
    except Exception as e:
        print(f"[DEBUG] Health check failed: {e} — proceeding anyway", flush=True)

    for task in TASKS:
        print(f"\n[DEBUG] === Running task: {task} ===", flush=True)
        run_task(client, task)
        print("", flush=True)

if __name__ == "__main__":
    main()