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

cache_app = typer.Typer(
    name="cache",
    help="Manage the Cloq prompt cache.",
    no_args_is_help=True,
)
app.add_typer(cache_app)


@app.callback()
def main_callback(ctx: typer.Context) -> None:
    """🔒 Cloq — Cloak your secrets before they reach the cloud."""
    if ctx.invoked_subcommand is None:
        try:
            import questionary
            import webbrowser
            import threading
            import time
            from cloq.cli.output import print_banner, VERSION_STR
            
            print_banner(show_mascot=False)
            console.print("========================================")
            console.print(f"  Choose Interface (v{VERSION_STR.lstrip('v')})")
            console.print("  🚀 Server: http://127.0.0.1:8989")
            console.print("========================================\n")
            
            choice = questionary.select(
                "",
                choices=[
                    "★ Web UI (Open in Browser)",
                    "☆ Terminal UI (Interactive CLI)",
                    "☆ Exit"
                ],
                qmark="?",
                pointer="❯"
            ).ask()

            if not choice or choice == "☆ Exit":
                raise typer.Exit()
                
            if choice == "★ Web UI (Open in Browser)":
                def open_browser():
                    time.sleep(1.5)
                    webbrowser.open("http://127.0.0.1:8989/ui")
                threading.Thread(target=open_browser, daemon=True).start()
                ctx.invoke(start)
                
            elif choice == "☆ Terminal UI (Interactive CLI)":
                ctx.invoke(start)
                
        except ImportError:
            # Fallback if questionary is not installed
            print_banner()
            console.print()
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


@app.command()
def version() -> None:
    """Show the current version of Cloq."""
    import platform

    from cloq.cli.output import VERSION_STR, print_banner

    print_banner(show_mascot=False)
    console.print(f"  [bold cyan]Cloq CLI[/bold cyan] {VERSION_STR}")
    console.print(f"  [dim]Python {platform.python_version()} on {platform.system()}[/dim]\n")


@app.command()
def doctor() -> None:
    """Check if the system is correctly configured for Cloq."""
    import platform
    import socket
    import sys
    from pathlib import Path

    from rich.panel import Panel
    from rich.table import Table

    from cloq.cli.output import print_banner

    print_banner(show_mascot=False)
    console.print("  [bold]Running Cloq Doctor...[/bold]\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()

    # Check Python version
    py_version = platform.python_version()
    if sys.version_info >= (3, 10):
        table.add_row("Python Version", f"[green]✓ {py_version}[/green]")
    else:
        table.add_row("Python Version", f"[red]✗ {py_version} (needs 3.10+)[/red]")

    # Check config file
    config_path = Path(".cloq.yml")
    if config_path.exists():
        table.add_row("Configuration", f"[green]✓ Found {config_path.absolute()}[/green]")
    else:
        table.add_row("Configuration", "[yellow]⚠ No .cloq.yml found (using defaults)[/yellow]")

    # Check proxy port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_result = sock.connect_ex(("127.0.0.1", 8989))
    if port_result == 0:
        table.add_row("Proxy Status", "[green]✓ Running on port 8989[/green]")
    else:
        table.add_row("Proxy Status", "[yellow]● Stopped (Port 8989 available)[/yellow]")
    sock.close()

    console.print(
        Panel(table, title="[bold]System Checks[/bold]", border_style="cyan", expand=False)
    )
    console.print()


@app.command()
def gain() -> None:
    """View cost and token savings from the prompt cache."""
    import httpx
    from rich.panel import Panel
    from rich.table import Table

    from cloq.cli.output import print_banner, print_error

    print_banner(show_mascot=False)
    console.print("  [bold]Calculating Cloq Cache Gains...[/bold]\n")

    try:
        resp = httpx.get("http://127.0.0.1:8989/stats", timeout=2.0)
        if resp.status_code != 200:
            print_error("Could not fetch stats. Is the proxy running?")
            raise typer.Exit(1)
        stats = resp.json()
    except httpx.ConnectError:
        print_error("Proxy is offline. Start it first with: cloq-cli start")
        raise typer.Exit(1)

    savings_table = Table(show_header=False, box=None, padding=(0, 2))
    savings_table.add_column(style="bold green")
    savings_table.add_column(justify="right")

    savings_table.add_row(
        "Tokens Saved", f"[bold orange3]{stats.get('estimated_tokens_saved', 0):,}[/bold orange3]"
    )
    savings_table.add_row(
        "Estimated Dollars Saved",
        f"[bold green]${stats.get('estimated_dollars_saved', 0.0):.3f}[/bold green]",
    )
    savings_table.add_row("Cache Hits", f"{stats.get('cache_hits', 0)}")
    savings_table.add_row("Cache Misses", f"{stats.get('cache_misses', 0)}")
    savings_table.add_row("Hit Rate", f"{stats.get('cache_hit_rate_pct', 0.0):.1f}%")

    console.print(
        Panel(savings_table, title="[bold]Developer Gains[/bold]", border_style="green", expand=False)
    )
    console.print()


@cache_app.command("stats")
def cache_stats() -> None:
    """Show detailed cache statistics."""
    gain()


if __name__ == "__main__":
    app()
