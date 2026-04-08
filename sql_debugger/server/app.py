# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
FastAPI application for the Sql Debugger Environment.
"""

try:
    from openenv.core.env_server.http_server import create_app  # type: ignore
except Exception as e:
    raise ImportError(
        "openenv is required. Install dependencies with:\n    uv sync\n"
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
    Entry point for validator + Docker + HF Spaces
    """
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()