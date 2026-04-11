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
        print(f"[WARN] HF error: {e}")
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
        "easy": "Fix the SQL syntax error",
        "medium": "Fix the SQL logic error",
        "hard": "Optimize the SQL query for performance",
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


def run():
    if not API_KEY:
        raise ValueError("API_KEY or HF_TOKEN is required")

    global client
    client = OpenAI(
        base_url=API_BASE_URL or "https://api-inference.huggingface.co/v1",
        api_key=API_KEY,
    )

    env = SqlDebuggerEnvironment()
    obs: SqlDebuggerObservation = env.reset()

    print("[START] task=sql_debugger", flush=True)

    rewards = []
    done = False
    prev_query = None

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

        print(f"Step {step} Query: {query}")
        print(f"Result: {obs.execution_result}")
        print(f"Base Reward: {base_reward:.2f} | Penalty: {penalty:.2f} | Final: {final_reward:.2f}")
        print(f"Done: {done}\n")
        print(f"[STEP] step={step} reward={final_reward:.2f}", flush=True)

        prev_query = query

        if done:
            break

    total = sum(rewards)

    print("=" * 40)
    print(f"Solved: {done}")
    print(f"Steps: {step}")
    print(f"Total Reward: {total:.2f}")
    print("=" * 40)
    print(f"[END] task=sql_debugger score={total:.2f} steps={step}", flush=True)


if __name__ == "__main__":
    run()