# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Sql Debugger Environment Implementation.

An RL environment for SQL debugging tasks (syntax, logic, optimization).
"""

import sqlite3
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment  # type: ignore[import]
from openenv.core.env_server.types import State  # type: ignore[import]

try:
    from ..models import SqlDebuggerAction, SqlDebuggerObservation
except ImportError:
    from models import SqlDebuggerAction, SqlDebuggerObservation  # type: ignore[import]


class SqlDebuggerEnvironment(Environment):
    """
    RL Environment for SQL debugging tasks.

    Supports three task types:
      - syntax:   Fix a broken SQL query.
      - logic:    Fix a query that runs but returns wrong results.
      - optimize: Improve query efficiency while keeping results correct.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        """Initialize the sql_debugger environment."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._reset_count = 0

        # SQLite in-memory DB
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        self._setup_db()

        # RL state
        self.expected_result = []
        self.previous_query = None
        self.previous_cost = float('inf')
        self.task_type = None
        self.initial_query = None

    
    # DATABASE SETUP
    
    def _setup_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER,
                name TEXT,
                age INTEGER
            )
        """)
        self.cursor.executemany("""
            INSERT INTO users VALUES (?, ?, ?)
        """, [
            (1, 'Alice', 25),
            (2, 'Bob', 30),
            (3, 'Charlie', 35)
        ])
        self.conn.commit()

    # QUERY EXECUTION
    def run_query(self, query):
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall(), None
        except Exception as e:
            return None, str(e)

    # RESULT COMPARISON
    def compare_results(self, result):
        if result is None:
            return False, False
        row_match = len(result) == len(self.expected_result)
        value_match = result == self.expected_result
        return row_match, value_match

    
    # COST (OPTIMIZATION)
    
    def get_query_cost(self, query):
        try:
            self.cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            plan = self.cursor.fetchall()
            cost = len(plan)
            for row in plan:
                if "SCAN" in str(row).upper():
                    cost += 2
            return cost
        except Exception:
            return float('inf')

    # REWARD FUNCTION
    def compute_reward(self, query, result, error):
        reward = 0

        # Execution check
        if error is None:
            reward += 0.2
        else:
            reward -= 0.3
            return reward

        row_match, value_match = self.compare_results(result)

        if self.task_type == "syntax":
            if row_match:
                reward += 0.3
            if value_match:
                reward += 0.5

        elif self.task_type == "logic":
            if row_match:
                reward += 0.3
            if value_match:
                reward += 0.5

            # improvement tracking
            if self.previous_query:
                prev_result, _ = self.run_query(self.previous_query)
                prev_row, prev_val = self.compare_results(prev_result)
                if (row_match and not prev_row) or (value_match and not prev_val):
                    reward += 0.2

        else:  # optimize
            if not value_match:
                return reward

            reward += 0.5

            current_cost = self.get_query_cost(query)

            if current_cost < self.previous_cost:
                reward += 0.3
            elif current_cost > self.previous_cost:
                reward -= 0.2

            self.previous_cost = current_cost

        # Penalties
        if query == self.previous_query:
            reward -= 0.1

        if any(word in query.upper() for word in ["DROP", "DELETE", "UPDATE"]):
            reward -= 0.5

        return reward

    
    # RESET
    
    def reset(self) -> SqlDebuggerObservation:
        """Reset the environment and pick a random task."""
        import random

        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._reset_count += 1
        self.previous_query = None
        self.previous_cost = float('inf')

        self.task_type = random.choice(["syntax", "logic", "optimize"])

        if self.task_type == "syntax":
            self.initial_query = "SELEC name FROM users"
            self.expected_result = [('Alice',), ('Bob',), ('Charlie',)]
            hint = "The query has a syntax error"
            self.difficulty = "easy"

        elif self.task_type == "logic":
            self.initial_query = "SELECT name FROM users WHERE age > 35"
            self.expected_result = [('Bob',), ('Charlie',)]
            hint = "The query runs but gives wrong results"
            self.difficulty = "medium"

        else:  # optimize
            self.initial_query = "SELECT * FROM users WHERE age > 28"
            self.expected_result = [('Bob', 30), ('Charlie', 35)]
            hint = "The query is correct but inefficient"
            self.difficulty = "hard"

        schema = {
            "tables": {
                "users": {
                    "columns": ["id (INTEGER)", "name (TEXT)", "age (INTEGER)"],
                    "sample_rows": 3
                }
            }
        }

        return SqlDebuggerObservation(
            broken_query=self.initial_query,
            schema_json=schema,
            expected_output_hint=hint,
            step_count=self._state.step_count,
            max_steps=5,
            difficulty=self.difficulty,
        )

    
    # STEP
    def step(self, action: SqlDebuggerAction) -> SqlDebuggerObservation:  # type: ignore[override]
        """
        Execute a step: run the agent's fixed SQL query and compute reward.

        Args:
            action: SqlDebuggerAction containing fixed_query and optional explanation.

        Returns:
            SqlDebuggerObservation with reward, done flag, and feedback.
        """
        self._state.step_count += 1

        query = action.fixed_query  # updated from action.message
        result, error = self.run_query(query)
        reward = self.compute_reward(query, result, error)

        done = (result == self.expected_result)

        self.previous_query = query

        schema = {
            "tables": {
                "users": {
                    "columns": ["id (INTEGER)", "name (TEXT)", "age (INTEGER)"],
                    "sample_rows": 3
                }
            }
        }

        return SqlDebuggerObservation(
            broken_query=self.initial_query,
            schema_json=schema,
            error_message=error,
            execution_result=result,
            step_count=self._state.step_count,
            max_steps=5,
            last_action=query,
            last_reward=reward,
            difficulty=getattr(self, 'difficulty', 'medium'),
        )

    
    # STATE PROPERTY
    
    @property
    def state(self) -> State:
        """Get the current environment state."""
        return self._state
