"""Rich-powered terminal output for Cloq CLI."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# ── ASCII banner ─────────────────────────────────────────────────────
BANNER = r"""
   _____ _
  / ____| |
 | |    | | ___   __ _
 | |    | |/ _ \ / _` |
 | |____| | (_) | (_| |
  \_____|_|\___/ \__, |
                    | |
                    |_|
"""

TAGLINE = "🔒 Cloak your secrets before they reach the cloud"


def print_banner() -> None:
    """Print the Cloq ASCII banner with styling."""
    text = Text(BANNER, style="bold cyan")
    console.print(text)
    console.print(f"  {TAGLINE}\n", style="dim")


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
