---
title: Sql Debugger Environment Server
emoji: 🛠️
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - sql
  - reinforcement-learning
---

# 🛠️ SQL Debugger Environment

An **OpenEnv-compatible Reinforcement Learning environment** where an AI agent learns to fix and optimize SQL queries. The agent receives a broken SQL query and must return a corrected version, earning rewards based on how well it fixes syntax errors, logic bugs, or query inefficiency.

---

## 🤖 How the Automated Validation Works

> **This environment is fully automated.** The OpenEnv validation pipeline runs `inference.py` automatically — no manual testing is required by judges.

The pipeline:
1. Resets the environment (`POST /reset`) → gets a broken SQL query
2. Runs `inference.py` → the AI agent generates fixed queries step by step
3. Reads the structured stdout output for `[START]`, `[STEP]`, and `[END]` blocks
4. Scores the submission based on total reward accumulated

---

## 🎮 The Three Task Types

The environment randomly selects one of three task types on each reset:

| Difficulty | Broken Query | What's Wrong | Expected Output |
|---|---|---|---|
| `easy` | `SELEC name FROM users` | Syntax typo (`SELEC` instead of `SELECT`) | `[('Alice',), ('Bob',), ('Charlie',)]` |
| `medium` | `SELECT name FROM users WHERE age > 35` | Logic error (no one is over 35) | `[('Bob',), ('Charlie',)]` |
| `hard` | `SELECT * FROM users WHERE age > 28` | Inefficient (`SELECT *` fetches unneeded columns) | `[('Bob', 30), ('Charlie', 35)]` |

### Correct Fix for Each Task

```sql
-- easy: fix the typo
SELECT name FROM users

-- medium: fix the logic (age >= 30, not > 35)
SELECT name FROM users WHERE age >= 30

-- hard: optimize (select only needed columns)
SELECT name, age FROM users WHERE age > 28
```

---

## 🗄️ Database Schema

The environment uses a simple in-memory SQLite database:

```sql
CREATE TABLE users (
    id   INTEGER,
    name TEXT,
    age  INTEGER
);

-- Data:
-- (1, 'Alice', 25)
-- (2, 'Bob',   30)
-- (3, 'Charlie', 35)
```

---

## 🏆 Reward Function

| Condition | Reward |
|---|---|
| Query runs without error | +0.2 |
| Correct number of rows returned | +0.3 |
| Exact values match expected output | +0.5 |
| Using `SELECT *` (penalized) | -0.3 |
| Submitting same query twice | -0.1 |
| Using `DROP`/`DELETE`/`UPDATE` | -0.5 |
| **Maximum per step** | **1.0** |

---

## 🚀 Manual Testing via the Web Interface

You can manually test the environment using the interactive UI on this Space:

### Step 1 — Reset (Start a new episode)
Click **Reset** to start a fresh episode. The response tells you which task was randomly assigned:
```json
{
  "observation": {
    "broken_query": "SELEC name FROM users",
    "difficulty": "easy",
    "expected_output_hint": "The query has a syntax error"
  }
}
```

### Step 2 — Check `difficulty`, submit the right fix
Enter your fixed query in the **Fixed Query** box and click **Step**:

```
Fixed Query: SELECT name FROM users
```

### Step 3 — Read the result
A perfect response looks like:
```json
{
  "observation": {
    "execution_result": [["Alice"], ["Bob"], ["Charlie"]],
    "last_reward": 1.0,
    "difficulty": "easy"
  },
  "done": false
}
```
`last_reward: 1.0` = maximum score ✅

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/reset` | POST | Start a new episode, get broken query |
| `/step` | POST | Submit a fixed query, get reward |
| `/health` | GET | Check if server is running |
| `/docs` | GET | Full OpenAPI / Swagger docs |
| `/web` | GET | Interactive web UI |

### cURL Examples

```bash
# Reset - start new episode
curl -X POST https://gagandeep6378-sql-debugger.hf.space/reset \
  -H "Content-Type: application/json" -d '{}'

# Step - submit a fixed query
curl -X POST https://gagandeep6378-sql-debugger.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"fixed_query": "SELECT name FROM users"}}'

# Health check
curl https://gagandeep6378-sql-debugger.hf.space/health
```

---

## 🐍 Python Client Usage

```python
from sql_debugger import SqlDebuggerEnv, SqlDebuggerAction

env = SqlDebuggerEnv(base_url="https://gagandeep6378-sql-debugger.hf.space")

obs = env.reset()
print(f"Task: {obs.observation.difficulty}")
print(f"Broken query: {obs.observation.broken_query}")

# Submit the fix
result = env.step(SqlDebuggerAction(fixed_query="SELECT name FROM users WHERE age >= 30"))
print(f"Reward: {result.observation.last_reward}")
print(f"Result: {result.observation.execution_result}")
```

---

## 📁 Project Structure

```
sql_debugger/
├── README.md                        # This file
├── openenv.yaml                     # OpenEnv manifest
├── pyproject.toml                   # Dependencies
├── inference.py                     # 🤖 AI agent (runs automatically during validation)
├── models.py                        # Action & Observation data models
├── client.py                        # Python client helper
└── server/
    ├── app.py                       # FastAPI server (HTTP + WebSocket)
    ├── sql_debugger_environment.py  # Core RL environment logic
    └── Dockerfile                   # Container definition
```

---

## 🧪 Running the Validation Locally

```bash
# From the sql_debugger/ directory
openenv validate
```

Expected output:
```
[OK] sql_debugger: Ready for multi-mode deployment
```
