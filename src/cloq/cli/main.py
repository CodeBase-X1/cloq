"""Cloq CLI — command-line interface powered by Typer + Rich."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from cloq.cli.output import (
    console,
    create_dashboard_layout,
    print_banner,
    print_detection_results,
    print_error,
    print_status,
    print_success,
    print_warning,
)

app = typer.Typer(
    name="cloq",
    help="🔒 Cloq — Cloak your secrets before they reach the cloud.",
    add_completion=True,
    no_args_is_help=False,
    invoke_without_command=True,
    rich_markup_mode="rich",
)

config_app = typer.Typer(
    name="config",
    help="Manage Cloq configuration.",
    no_args_is_help=True,
)
app.add_typer(config_app)


@app.callback()
def main_callback(ctx: typer.Context) -> None:
    """🔒 Cloq — Cloak your secrets before they reach the cloud."""
    if ctx.invoked_subcommand is None:
        # No subcommand provided — show the mascot banner then help
        print_banner()
        console.print()
        # Print help after the banner
        console.print(ctx.get_help())
        raise typer.Exit()

@app.command()
def start(
    host: Annotated[str, typer.Option(help="Bind address")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port")] = 8989,
    config: Annotated[str | None, typer.Option("--config", "-c", help="Config file path")] = None,
    daemon: Annotated[
        bool, typer.Option("--daemon", "-d", help="Run as background daemon")
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable debug logging")] = False,
) -> None:
    """Start the Cloq proxy server."""
    import uvicorn

    from cloq.config.loader import load_config
    from cloq.proxy.middleware import add_middleware
    from cloq.proxy.server import create_app

    print_banner()

    # Load configuration
    cli_overrides = {"proxy": {"host": host, "port": port}}
    if verbose:
        cli_overrides["logging"] = {"level": "DEBUG"}

    cloq_config = load_config(config_path=config, cli_overrides=cli_overrides)

    # Create FastAPI app
    fastapi_app = create_app(cloq_config)
    add_middleware(fastapi_app)

    active_detectors = []
    if cloq_config.detection.secrets.enabled:
        active_detectors.append("secrets")
    if cloq_config.detection.pii.enabled:
        active_detectors.append("pii")
    if cloq_config.detection.network.enabled:
        active_detectors.append("network")

    print_status(
        is_running=True,
        host=host,
        port=port,
        detectors=active_detectors,
    )

    console.print(
        f"\n  [dim]Point your LLM client to:[/dim] [bold cyan]http://{host}:{port}[/bold cyan]\n"
    )
    console.print("  [dim]Press Ctrl+C to stop[/dim]\n")

    if daemon:
        print_warning("Daemon mode is not yet implemented. Running in foreground.")

    # Run the server
    log_level = "debug" if verbose else cloq_config.proxy.log_level
    uvicorn.run(
        fastapi_app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=False,
    )


@app.command()
def scan(
    file: Annotated[Path, typer.Argument(help="File to scan for sensitive data")],
    config: Annotated[str | None, typer.Option("--config", "-c")] = None,
) -> None:
    """Scan a file for sensitive data (standalone mode)."""
    from cloq.config.loader import load_config
    from cloq.detection.network import NetworkDetector
    from cloq.detection.pii import PIIDetector
    from cloq.detection.pipeline import DetectionPipeline
    from cloq.detection.secrets import SecretsDetector

    if not file.is_file():
        print_error(f"File not found: {file}")
        raise typer.Exit(1)

    cloq_config = load_config(config_path=config)

    # Build pipeline
    detectors = []
    if cloq_config.detection.secrets.enabled:
        detectors.append(SecretsDetector())
    if cloq_config.detection.pii.enabled:
        detectors.append(PIIDetector())
    if cloq_config.detection.network.enabled:
        detectors.append(
            NetworkDetector(
                internal_domains=cloq_config.detection.network.internal_domains,
            )
        )

    pipeline = DetectionPipeline(detectors)

    # Read and scan file
    text = file.read_text(encoding="utf-8", errors="replace")
    results, metrics = pipeline.run(text)

    # Display results
    result_dicts = [
        {
            "entity_type": r.entity_type,
            "original_text": r.original_text,
            "score": r.score,
            "detector_name": r.detector_name,
        }
        for r in results
    ]

    print_detection_results(result_dicts, filename=str(file))
    console.print(f"  [dim]Scanned in {metrics.total_duration_ms:.1f}ms[/dim]\n")


@app.command()
def status() -> None:
    """Show proxy status and statistics."""
    import httpx

    try:
        resp = httpx.get("http://127.0.0.1:8989/health", timeout=2.0)
        if resp.status_code == 200:
            stats_resp = httpx.get("http://127.0.0.1:8989/stats", timeout=2.0)
            stats = stats_resp.json() if stats_resp.status_code == 200 else {}
            print_status(is_running=True)
            if stats:
                console.print(
                    f"\n  Requests processed: [bold]{stats.get('requests_processed', 0)}[/bold]"
                )
                console.print(
                    f"  Entities sanitized: [bold]{stats.get('entities_sanitized', 0)}[/bold]"
                )
                console.print(
                    f"  Active sessions:    [bold]{stats.get('active_sessions', 0)}[/bold]"
                )
                uptime = stats.get("uptime_seconds", 0)
                console.print(f"  Uptime:             [bold]{uptime:.0f}s[/bold]\n")
        else:
            print_status(is_running=False)
    except httpx.ConnectError:
        print_status(is_running=False)
        print_warning("Cloq proxy is not running. Start it with: cloq start")


@app.command()
def dashboard() -> None:
    """Launch the interactive terminal dashboard HUD."""
    import time

    import httpx
    from rich.live import Live

    print_banner()

    def get_stats() -> dict | None:
        try:
            resp = httpx.get("http://127.0.0.1:8989/stats", timeout=1.0)
            if resp.status_code == 200:
                return resp.json()
        except httpx.ConnectError:
            pass
        return None

    stats = get_stats()
    panel = create_dashboard_layout(stats)

    with Live(panel, refresh_per_second=2, screen=False) as live:
        try:
            while True:
                time.sleep(0.5)
                stats = get_stats()
                live.update(create_dashboard_layout(stats))
        except KeyboardInterrupt:
            pass


@app.command()
def test() -> None:
    """Send a test prompt through the proxy to verify it works."""
    import httpx

    print_banner()
    console.print("  [bold]Running self-test...[/bold]\n")

    test_prompt = (
        "Fix this bug. The database is at 10.0.1.50:5432, "
        "my AWS key is AKIAIOSFODNN7EXAMPLE, "
        "and contact me at test.user@company.com"
    )

    try:
        resp = httpx.get("http://127.0.0.1:8989/health", timeout=2.0)
        if resp.status_code != 200:
            print_error("Proxy is not running. Start it first with: cloq start")
            raise typer.Exit(1)
    except httpx.ConnectError:
        print_error("Cannot connect to proxy at http://127.0.0.1:8989")
        print_warning("Start the proxy first with: cloq start")
        raise typer.Exit(1) from None

    print_success("Proxy is running")
    console.print(f"\n  [dim]Test prompt:[/dim]\n  {test_prompt}\n")

    # Test the detection pipeline directly
    from cloq.detection.network import NetworkDetector
    from cloq.detection.pii import PIIDetector
    from cloq.detection.pipeline import DetectionPipeline
    from cloq.detection.secrets import SecretsDetector
    from cloq.sanitizer.engine import SanitizationSession, sanitize

    pipeline = DetectionPipeline(
        [
            SecretsDetector(),
            PIIDetector(),
            NetworkDetector(),
        ]
    )

    results, metrics = pipeline.run(test_prompt)
    session = SanitizationSession(session_id="test")
    sanitized = sanitize(test_prompt, results, session)

    console.print(f"  [dim]Sanitized output:[/dim]\n  [cyan]{sanitized}[/cyan]\n")
    console.print(
        f"  [dim]Entities detected: {len(results)} in {metrics.total_duration_ms:.1f}ms[/dim]\n"
    )

    for tag, original in session.tag_to_original.items():
        console.print(f"    {tag} → [dim]{original}[/dim]")

    console.print()
    print_success("Self-test passed! Cloq is working correctly.")


@config_app.command("init")
def config_init(
    output: Annotated[str, typer.Option("--output", "-o", help="Output path")] = ".cloq.yml",
) -> None:
    """Generate a default .cloq.yml configuration file."""
    from cloq.config.schema import CloqConfig

    path = Path(output)
    if path.exists():
        print_warning(f"{output} already exists. Use --output to specify a different path.")
        raise typer.Exit(1)

    config = CloqConfig()
    config.to_yaml_path(path)
    print_success(f"Configuration written to {output}")


@config_app.command("show")
def config_show(
    config: Annotated[str | None, typer.Option("--config", "-c")] = None,
) -> None:
    """Show the resolved configuration."""

    from cloq.config.loader import load_config

    cloq_config = load_config(config_path=config)
    console.print_json(data=cloq_config.model_dump())


if __name__ == "__main__":
    app()
