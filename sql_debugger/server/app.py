# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Sql Debugger Environment.

This module creates an HTTP server that exposes the SqlDebuggerEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""

try:
    from openenv.core.env_server.http_server import create_app  # type: ignore[import]
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import SqlDebuggerAction, SqlDebuggerObservation
    from .sql_debugger_environment import SqlDebuggerEnvironment
except ImportError:
    from models import SqlDebuggerAction, SqlDebuggerObservation  # type: ignore[import]
    from server.sql_debugger_environment import SqlDebuggerEnvironment  # type: ignore[import]


# Create the app with web interface and README integration
app = create_app(
    SqlDebuggerEnvironment,
    SqlDebuggerAction,
    SqlDebuggerObservation,
    env_name="sql_debugger",
    max_concurrent_envs=1,  # increase this number to allow more concurrent WebSocket sessions
)


def main():
    """
    Entry point for OpenEnv validation and direct execution.
    """
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
