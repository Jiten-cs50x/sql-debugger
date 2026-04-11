import os
import json
import re
import warnings
warnings.filterwarnings("ignore")
from openai import OpenAI

from sql_debugger.server.sql_debugger_environment import SqlDebuggerEnvironment
from sql_debugger.models import SqlDebuggerAction, SqlDebuggerObservation


# Use the validator-injected LiteLLM proxy if available, otherwise fall back to HF
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
MAX_STEPS = 5

client: OpenAI | None = None

# Three tasks we must run — each becomes a separate [START]/[END] block
TASKS = [
    ("syntax",   "sql_debugger_syntax"),
    ("logic",    "sql_debugger_logic"),
    ("optimize", "sql_debugger_optimize"),
]


def generate_action(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.1,
        )
        text = response.choices[0].message.content or ""
        return extract_sql(text.strip())

    except Exception as e:
        print(f"[WARN] LLM error: {e}")
        return "SELECT name FROM users"


def extract_sql(text: str) -> str:
    match = re.search(r"```(?:sql)?\s*\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    sql_keywords = ("SELECT", "INSERT", "CREATE", "ALTER", "WITH", "EXPLAIN")
    for line in text.splitlines():
        if line.strip().upper().startswith(sql_keywords):
            return line.strip()

    return text.strip()


def build_prompt(obs: SqlDebuggerObservation) -> str:
    task_map = {
        "easy":   "Fix the SQL syntax error",
        "medium": "Fix the SQL logic error",
        "hard":   "Optimize the SQL query for performance",
    }

    task = task_map.get(obs.difficulty, "Fix the SQL query")
    schema = json.dumps(obs.schema_json, indent=2)

    feedback = ""
    if obs.error_message:
        feedback += f"\nPrevious Error: {obs.error_message}"
    if obs.execution_result is not None:
        feedback += f"\nPrevious Result: {obs.execution_result}"
    if obs.last_reward is not None:
        feedback += f"\nPrevious Reward: {obs.last_reward:.2f}"

    return f"""You are an expert SQL optimizer.

Task: {task}
Broken query: {obs.broken_query}
Hint: {obs.expected_output_hint or 'None'}

Schema:
{schema}
{feedback}

STRICT RULES:
- Do NOT use SELECT *
- Select ONLY required columns
- Prefer minimal and efficient queries
- Avoid unnecessary subqueries
- Keep output logically identical

Return ONLY the SQL query. No explanation.
"""


def apply_penalty(query: str, prev_query: str | None) -> float:
    penalty = 0.0
    q = query.upper()

    if "SELECT *" in q:
        penalty -= 0.3

    if prev_query and query.strip() == prev_query.strip():
        penalty -= 0.2

    if "IN (" in q or "SELECT" in q and "GROUP BY" in q:
        penalty -= 0.1

    return penalty


def force_task(env: SqlDebuggerEnvironment, task_type: str) -> SqlDebuggerObservation:
    """Reset the environment and then override to a specific task type."""
    from uuid import uuid4
    from openenv.core.env_server.types import State  # type: ignore[import]

    env._state = State(episode_id=str(uuid4()), step_count=0)
    env._reset_count += 1
    env.previous_query = None
    env.previous_cost = float('inf')
    env.task_type = task_type

    schema = {
        "tables": {
            "users": {
                "columns": ["id (INTEGER)", "name (TEXT)", "age (INTEGER)"],
                "sample_rows": 3
            }
        }
    }

    if task_type == "syntax":
        env.initial_query = "SELEC name FROM users"
        env.expected_result = [('Alice',), ('Bob',), ('Charlie',)]
        env.difficulty = "easy"
        hint = "The query has a syntax error"

    elif task_type == "logic":
        env.initial_query = "SELECT name FROM users WHERE age > 35"
        env.expected_result = [('Bob',), ('Charlie',)]
        env.difficulty = "medium"
        hint = "The query runs but gives wrong results"

    else:  # optimize
        env.initial_query = "SELECT * FROM users WHERE age > 28"
        env.expected_result = [('Bob', 30), ('Charlie', 35)]
        env.difficulty = "hard"
        hint = "The query is correct but inefficient"

    return SqlDebuggerObservation(
        broken_query=env.initial_query,
        schema_json=schema,
        expected_output_hint=hint,
        step_count=0,
        max_steps=MAX_STEPS,
        difficulty=env.difficulty,
    )


def clamp_score(raw: float) -> float:
    """Ensure score is strictly between 0 and 1 as required by the validator."""
    return max(0.01, min(0.99, raw))


def run_episode(task_type: str, task_name: str) -> None:
    """Run a single episode for one task type, printing structured output."""
    env = SqlDebuggerEnvironment()
    obs = force_task(env, task_type)

    print(f"[START] task={task_name}", flush=True)

    rewards = []
    done = False
    prev_query = None
    step = 0

    for step in range(1, MAX_STEPS + 1):
        prompt = build_prompt(obs)
        query = generate_action(prompt)

        action = SqlDebuggerAction(fixed_query=query)
        obs = env.step(action)

        base_reward = obs.last_reward or 0.0
        penalty = apply_penalty(query, prev_query)
        final_reward = base_reward + penalty

        rewards.append(final_reward)
        done = obs.execution_result == env.expected_result

        print(f"Step {step} | Task: {task_name} | Query: {query}")
        print(f"  Result: {obs.execution_result}")
        print(f"  Base: {base_reward:.2f} | Penalty: {penalty:.2f} | Final: {final_reward:.2f} | Done: {done}")
        print(f"[STEP] step={step} reward={final_reward:.4f}", flush=True)

        prev_query = query

        if done:
            break

    # Normalize: divide by MAX_STEPS so max possible is 1.0, then clamp to (0.01, 0.99)
    raw_score = sum(rewards) / MAX_STEPS
    score = clamp_score(raw_score)

    print(f"[END] task={task_name} score={score:.4f} steps={step}", flush=True)


def run():
    if not API_KEY:
        raise ValueError("API_KEY or HF_TOKEN is required")

    global client
    client = OpenAI(
        base_url=API_BASE_URL or "https://api-inference.huggingface.co/v1",
        api_key=API_KEY,
    )

    print("=" * 50)
    print("SQL Debugger — Running 3 tasks for evaluation")
    print("=" * 50)

    for task_type, task_name in TASKS:
        print(f"\n--- Starting: {task_name} ---")
        run_episode(task_type, task_name)
        print(f"--- Finished: {task_name} ---\n")

    print("=" * 50)
    print("All 3 tasks complete.")
    print("=" * 50)


if __name__ == "__main__":
    run()