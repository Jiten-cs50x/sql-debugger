# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Sql Debugger Environment.

This module creates an HTTP server that exposes the SqlDebuggerEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.
"""

try:
    from openenv.core.env_server.http_server import create_app  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with:\n    uv sync\n"
    ) from e

try:
    from ..models import SqlDebuggerAction, SqlDebuggerObservation
    from .sql_debugger_environment import SqlDebuggerEnvironment
except ImportError:
    from models import SqlDebuggerAction, SqlDebuggerObservation  # type: ignore
    from server.sql_debugger_environment import SqlDebuggerEnvironment  # type: ignore


# Create FastAPI app
app = create_app(
    SqlDebuggerEnvironment,
    SqlDebuggerAction,
    SqlDebuggerObservation,
    env_name="sql_debugger",
    max_concurrent_envs=1,
)


def main():
    """
    Entry point for running the server directly.

    This ensures compatibility with OpenEnv validator and Docker runtime.
    """
    import uvicorn

    # IMPORTANT: use string reference for validator compatibility
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()