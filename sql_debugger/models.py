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
    fixed_query: str = Field(..., description="The corrected SQL query")

    explanation: Optional[str] = Field(
        default=None,
        description="Optional explanation of the fix"
    )


class SqlDebuggerObservation(Observation):
    broken_query: str = Field(..., description="The SQL query that contains errors")

    schema_json: Dict[str, Any] = Field(
        ..., description="Database schema including tables, columns, and relationships"
    )

    error_message: Optional[str] = Field(
        default=None, description="Error message from SQLite"
    )

    execution_result: Optional[List[Any]] = Field(
        default=None, description="Query result if execution succeeds"
    )

    expected_output_hint: Optional[str] = Field(
        default=None, description="Hint about expected output"
    )

    step_count: int = Field(default=0)
    max_steps: int = Field(default=5)

    last_action: Optional[str] = Field(default=None)
    last_reward: Optional[float] = Field(default=None)

    difficulty: Optional[str] = Field(default="medium")