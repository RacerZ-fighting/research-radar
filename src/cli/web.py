"""Web console CLI command."""

from __future__ import annotations

import os

import click

from src.cli.main import AppContext, handle_command_errors, pass_app_context


@click.command("web")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host for the local web console.")
@click.option("--port", default=8000, show_default=True, type=click.IntRange(1, 65535), help="Port to bind.")
@click.option("--reload", is_flag=True, help="Enable uvicorn reload for local development.")
@pass_app_context
@handle_command_errors
def web_command(app: AppContext, host: str, port: int, reload: bool) -> None:
    """Start the local Research Radar web console."""

    os.environ["DATABASE_URL"] = app.database_url
    import uvicorn

    click.echo(f"Starting Research Radar web console at http://{host}:{port}")
    uvicorn.run("src.web.app:create_app", factory=True, host=host, port=port, reload=reload)
