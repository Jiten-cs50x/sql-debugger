# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Sql Debugger Environment.

The sql_debugger environment is a simple test environment that echoes back messages.
"""

from openenv.core.env_server.types import Action, Observation
from pydantic import Field
from typing import Optional, List, Dict, Any

class SqlDebuggerAction(Action):
    """Action for the Sql Debugger environment - just a message to echo."""

    message: str = Field(..., description="Message to echo back")


class SqlDebuggerObservation(Observation):

      # 🔹 Core problem
    broken_query: str = Field(..., description="The SQL query that contains errors")

    # 🔹 Database understanding
    schema_json: Dict[str, Any] = Field(
        ..., description="Database schema including tables, columns, and relationships"
    )

    # 🔹 Execution feedback
    error_message: Optional[str] = Field(
        default=None, description="Error message returned by SQLite when executing the broken query"
    )

    execution_result: Optional[List[Any]] = Field(
        default=None, description="Query result if execution succeeds (partial or full)"
    )

    # 🔹 Context awareness
    expected_output_hint: Optional[str] = Field(
        default=None,
        description="Hint about expected output (optional, helps learning/debugging)"
    )

    # 🔹 RL tracking
    step_count: int = Field(
        default=0, description="Current step number in the episode"
    )

    max_steps: int = Field(
        default=5, description="Maximum allowed steps in the episode"
    )

    # 🔹 Debugging signals
    last_action: Optional[str] = Field(
        default=None, description="Last query submitted by the agent"
    )

    last_reward: Optional[float] = Field(
        default=None, description="Reward received in the previous step"
    )

    # 🔹 Difficulty / metadata
    difficulty: Optional[str] = Field(
        default="medium", description="Task difficulty level"
    )
    """Observation from the Sql Debugger environment - the echoed message."""

    #echoed_message: str = Field(default="", description="The echoed message")
    #message_length: int = Field(default=0, description="Length of the echoed message")
