"""CLI application for MSNA 2025 analysis."""

import typer
from loguru import logger

from src.extraction import extract_data

app = typer.Typer(
    name="kmta",
    help="Kobo MSNA Template Analysis - Analyze Kobo forms compliance with MSNA 2025 template",
    add_completion=False,
)


@app.command()
def extract():
    """Extract data from database and save to parquet files."""
    try:
        extract_data()
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def info():
    """Display project information."""
    logger.info("MSNA 2025 Form Template Analysis")
    logger.info("Version: 0.1.0")
    logger.info("Description: Analyze Kobo form compliance with MSNA 2025 template")


if __name__ == "__main__":
    app()
