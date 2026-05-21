"""Rich-powered terminal output for Cloq CLI."""

from __future__ import annotations

import platform

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# ── Vibrant pixel-art welcome screen ─────────────────────────────────
# Uses Unicode block characters with Rich hex-color markup for a
# stunning multi-color gradient pixel-art splash, inspired by
# Claude Code, Gemini CLI, and GitHub Copilot CLI branding.

VERSION_STR = "v0.1.0"


def _build_colorful_banner() -> str:
    """Build the colorful pixel-art banner string with Rich markup."""
    # Shield with multi-color gradient (top→bottom: cyan → blue → purple → magenta)
    shield = [
        "[bold #00e5ff]              ░░░░░▓▓▓▓▓▓▓▓▓▓▓░░░░░[/]",
        "[bold #00d4ff]            ░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░[/]",
        "[bold #00c3ff]           ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓[/]",
        "[bold #00b0ff]          ▓▓▓▓▓[/][bold #ffffff]░░░░░░░░░░░░░░░[/][bold #00b0ff]▓▓▓▓▓[/]",
        "[bold #2196f3]          ▓▓▓▓[/][bold #ffffff]░░░[/][bold #ffab00]██████████████[/][bold #ffffff]░░░[/][bold #2196f3]▓▓▓▓[/]",
        "[bold #536dfe]          ▓▓▓▓[/][bold #ffffff]░░░[/][bold #ffd740]██[/][bold #ff6d00]██  ██████  ██[/][bold #ffd740]██[/][bold #ffffff]░░░[/][bold #536dfe]▓▓▓▓[/]",
        "[bold #7c4dff]          ▓▓▓▓[/][bold #ffffff]░░░[/][bold #ffd740]██[/][bold #ff6d00]██  ██████  ██[/][bold #ffd740]██[/][bold #ffffff]░░░[/][bold #7c4dff]▓▓▓▓[/]",
        "[bold #aa00ff]          ▓▓▓▓[/][bold #ffffff]░░░[/][bold #ffab00]██████████████[/][bold #ffffff]░░░[/][bold #aa00ff]▓▓▓▓[/]",
        "[bold #d500f9]           ▓▓▓▓[/][bold #ffffff]░░░░░░░░░░░░░░░[/][bold #d500f9]▓▓▓▓[/]",
        "[bold #e040fb]            ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓[/]",
        "[bold #ea80fc]              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓[/]",
        "[bold #f48fb1]                ▓▓▓▓▓▓▓▓▓▓▓▓▓[/]",
        "[bold #f8bbd0]                  ▓▓▓▓▓▓▓▓▓[/]",
        "[bold #fce4ec]                    ▓▓▓▓▓[/]",
        "[bold #ffffff]                      ▓[/]",
    ]

    # CLOQ text with rainbow gradient per line
    logo_text = [
        "",
        "[bold #00e5ff]         ██████╗[/][bold #00bfa5]██╗[/][bold #64dd17]      ██████╗ [/][bold #ffd600] ██████╗[/]",
        "[bold #00e5ff]        ██╔════╝[/][bold #00bfa5]██║[/][bold #64dd17]     ██╔═══██╗[/][bold #ffd600]██╔═══██╗[/]",
        "[bold #00b8d4]        ██║     [/][bold #00bfa5]██║[/][bold #64dd17]     ██║   ██║[/][bold #ffd600]██║   ██║[/]",
        "[bold #0091ea]        ██║     [/][bold #00bfa5]██║[/][bold #64dd17]     ██║   ██║[/][bold #ffab00]██║▄▄ ██║[/]",
        "[bold #304ffe]        ╚██████╗[/][bold #00bfa5]███████╗[/][bold #64dd17]╚██████╔╝[/][bold #ff6d00]╚██████╔╝[/]",
        "[bold #6200ea]         ╚═════╝[/][bold #00bfa5]╚══════╝[/][bold #64dd17] ╚═════╝ [/][bold #ff6d00] ╚══▀▀═╝[/]",
    ]

    # Tagline box with gradient border
    tagline = [
        "",
        "[#4dd0e1]      ┌─────────────────────────────────────────┐[/]",
        "[#4dd0e1]      │[/]  [bold #ff8a65]🔒[/] [bold white]Your secrets stay local.[/]               [#4dd0e1]│[/]",
        "[#4dd0e1]      │[/]  [bold #66bb6a]🧠[/] [bold white]Your LLM gets clean context.[/]           [#4dd0e1]│[/]",
        "[#4dd0e1]      │[/]  [bold #42a5f5]⚡[/] [bold white]Zero config. Zero latency. Zero cost.[/]  [#4dd0e1]│[/]",
        "[#4dd0e1]      └─────────────────────────────────────────┘[/]",
    ]

    return "\n".join(shield + logo_text + tagline)


def print_banner(show_shield: bool = True) -> None:
    """Print the Cloq colorful pixel-art welcome banner.

    Args:
        show_shield: If True (default), render the full pixel-art shield.
                     If False, show only the CLOQ text logo.
    """
    console.print()
    banner = _build_colorful_banner()
    console.print(banner)
    console.print()
    console.print(
        f"  [dim]Version {VERSION_STR}  •  "
        f"Python {platform.python_version()} on {platform.system()}"
        f"[/dim]\n"
    )


def print_status(
    is_running: bool,
    host: str = "127.0.0.1",
    port: int = 8989,
    detectors: list[str] | None = None,
) -> None:
    """Print proxy status information."""
    status = "[green]● Running[/green]" if is_running else "[red]● Stopped[/red]"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Status", status)
    table.add_row("Address", f"http://{host}:{port}")
    if detectors:
        table.add_row("Detectors", ", ".join(detectors))

    console.print(Panel(table, title="[bold]Cloq Proxy[/bold]", border_style="cyan"))


def print_detection_results(
    results: list[dict],
    filename: str | None = None,
) -> None:
    """Print detection results in a formatted table."""
    title = f"Scan Results: {filename}" if filename else "Scan Results"

    if not results:
        console.print(
            Panel("[green]✓ No sensitive data detected[/green]", title=title, border_style="green")
        )
        return

    table = Table(title=title, show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", style="bold")
    table.add_column("Value", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Detector")

    # Color-code by category
    type_colors = {
        "secret": "red",
        "pii": "yellow",
        "network": "blue",
    }

    for i, result in enumerate(results, 1):
        entity_type = result.get("entity_type", "UNKNOWN")
        detector = result.get("detector_name", "unknown")
        color = type_colors.get(detector, "white")

        # Mask the value for display
        original = result.get("original_text", "")
        masked = _mask_value(original)

        score = result.get("score", 0)
        score_color = "green" if score >= 0.9 else "yellow" if score >= 0.7 else "red"

        table.add_row(
            str(i),
            f"[{color}]{entity_type}[/{color}]",
            masked,
            f"[{score_color}]{score:.0%}[/{score_color}]",
            detector,
        )

    console.print(table)
    console.print(f"\n  [bold]{len(results)}[/bold] sensitive item(s) detected\n", style="dim")


def _mask_value(value: str, show_chars: int = 4) -> str:
    """Partially mask a sensitive value for safe display."""
    if len(value) <= show_chars * 2:
        return "●" * len(value)
    return value[:show_chars] + "●" * (len(value) - show_chars * 2) + value[-show_chars:]


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"  [green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"  [red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"  [yellow]⚠[/yellow] {message}")


def create_dashboard_layout(stats: dict | None) -> Panel:
    """Create a gorgeous terminal dashboard panel for Cloq status and savings."""
    if not stats:
        # Offline state
        offline_table = Table(show_header=False, box=None, padding=(1, 2))
        offline_table.add_column(style="bold red")
        offline_table.add_column()
        offline_table.add_row("Status", "● OFFLINE")
        offline_table.add_row(
            "Action",
            "[yellow]Start the proxy in another terminal with:[/yellow] [bold cyan]cloq start[/bold cyan]",
        )
        return Panel(
            offline_table,
            title="[bold red]Cloq Developer HUD[/bold red]",
            border_style="red",
            expand=False,
        )

    # Online state
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    # Column 1: Proxy Metrics
    metrics_table = Table(show_header=False, box=None, padding=(0, 1))
    metrics_table.add_column(style="bold cyan")
    metrics_table.add_column(justify="right")

    uptime = stats.get("uptime_seconds", 0)
    if uptime > 3600:
        uptime_str = f"{uptime / 3600:.1f}h"
    elif uptime > 60:
        uptime_str = f"{uptime / 60:.1f}m"
    else:
        uptime_str = f"{uptime:.0f}s"

    metrics_table.add_row("Uptime", uptime_str)
    metrics_table.add_row("Active Sessions", f"{stats.get('active_sessions', 0)}")
    metrics_table.add_row("Requests Intercepted", f"{stats.get('requests_processed', 0)}")
    metrics_table.add_row("Entities Masked", f"[red]{stats.get('entities_sanitized', 0)}[/red]")
    metrics_table.add_row(
        "Entities Restored", f"[green]{stats.get('entities_restored', 0)}[/green]"
    )

    # Column 2: Performance & Cost Savings
    savings_table = Table(show_header=False, box=None, padding=(0, 1))
    savings_table.add_column(style="bold yellow")
    savings_table.add_column(justify="right")
    savings_table.add_row("Cache Hits", f"[green]{stats.get('cache_hits', 0)}[/green]")
    savings_table.add_row("Cache Misses", f"[dim]{stats.get('cache_misses', 0)}[/dim]")
    savings_table.add_row(
        "Cache Hit Rate", f"[bold green]{stats.get('cache_hit_rate_pct', 0.0):.1f}%[/bold green]"
    )
    savings_table.add_row(
        "Tokens Saved", f"[bold orange3]{stats.get('estimated_tokens_saved', 0):,}[/bold orange3]"
    )
    savings_table.add_row(
        "Estimated Savings",
        f"[bold green]${stats.get('estimated_dollars_saved', 0.0):.3f}[/bold green]",
    )

    grid.add_row(
        Panel(metrics_table, title="[bold]Proxy Engine[/bold]", border_style="cyan"),
        Panel(savings_table, title="[bold]Cost Optimizer & Cache[/bold]", border_style="yellow"),
    )

    # Master Panel
    return Panel(
        grid,
        title="[bold green]● Cloq Developer HUD & Savings Dashboard[/bold green]",
        subtitle="[dim]Point client to http://127.0.0.1:8989 | Press Ctrl+C to exit[/dim]",
        border_style="green",
        expand=False,
    )
