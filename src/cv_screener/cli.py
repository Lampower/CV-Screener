"""CV Screener CLI — one Typer app, four commands: generate / index / search / chat."""

from __future__ import annotations

import sys

import typer
from openai import OpenAI
from rich.console import Console
from rich.progress import track

# Some Windows terminals use a legacy codepage that can't encode characters
# LLM output commonly contains (em dashes, curly quotes, etc.). Force UTF-8
# with a safe fallback so the chat REPL never crashes on an agent answer.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from cv_screener import db
from cv_screener.agent.chat_agent import build_llm, initial_history, run_turn
from cv_screener.config import PHOTOS_DIR, PROFILES_DIR, RESUMES_DIR, ensure_data_dirs
from cv_screener.generation.pdf_render import render_resume
from cv_screener.generation.photos import generate_headshot
from cv_screener.generation.profiles import generate_candidates
from cv_screener.indexing.build_index import build_index
from cv_screener.indexing.search import SearchResult, filter_search, hybrid_search, semantic_search

app = typer.Typer(help="CV Screener: generate synthetic candidates, index them, and chat over the dataset.")
console = Console()


def _require_db_or_exit() -> None:
    if not db.check_connection():
        console.print(
            "[red]Cannot connect to Postgres.[/red] Start it with "
            "[bold]docker compose up -d[/bold] and try again."
        )
        raise typer.Exit(1)


def _print_results(results: list[SearchResult]) -> None:
    if not results:
        console.print("[yellow]No matching candidates.[/yellow]")
        return
    for r in results:
        score = f"  (distance={r.score:.3f})" if r.score is not None else ""
        console.print(f"[bold]{r.full_name}[/bold] - {r.role}, {r.seniority}{score}")
        console.print(f"  {r.snippet}\n")


@app.command()
def generate(
    n: int = typer.Option(10, "--n", help="Number of candidates to generate (min 10 for the task)."),
    seed: int = typer.Option(None, "--seed", help="Random seed for reproducible generation."),
) -> None:
    """Generate N synthetic candidates: structured profile + LLM summary +
    AI headshot + one-page PDF resume. Writes data/profiles, data/photos,
    data/resumes."""
    ensure_data_dirs()
    console.print(f"Generating {n} synthetic candidates (this calls the OpenAI API: "
                  f"~1 chat completion + 1 image per candidate)...")
    candidates = generate_candidates(n, seed=seed)

    client = OpenAI()
    for profile in track(candidates, description="Rendering headshots + PDFs"):
        photo_path = generate_headshot(client, profile, PHOTOS_DIR)
        profile.photo_path = str(photo_path)
        pdf_path = RESUMES_DIR / f"{profile.id}.pdf"
        render_resume(profile, pdf_path)
        profile.resume_pdf_path = str(pdf_path)
        (PROFILES_DIR / f"{profile.id}.json").write_text(
            profile.model_dump_json(indent=2), encoding="utf-8"
        )

    console.print(f"[green]Done.[/green] {len(candidates)} candidates written to data/.")
    console.print("Next: [bold]docker compose up -d[/bold] then [bold]cvscreener index[/bold]")


@app.command()
def index() -> None:
    """(Re)build the search index from data/profiles/*.json — structured
    fields go into the `candidates` table, embeddings go into pgvector."""
    _require_db_or_exit()
    db.init_schema()
    n = build_index()
    console.print(f"[green]Indexed {n} candidates.[/green]")


@app.command()
def search(
    query: str = typer.Argument(None, help="Natural-language query for semantic search."),
    field: str = typer.Option(None, "--field", help="Structured field to filter on."),
    value: str = typer.Option(None, "--value", help="Value to filter for."),
    k: int = typer.Option(5, "--k", help="Max results to return."),
) -> None:
    """Search the indexed dataset. Pass a query for semantic search,
    --field/--value for exact field search, or both for hybrid (filter,
    then rank by similarity)."""
    _require_db_or_exit()
    if field and value and query:
        results = hybrid_search(query, field=field, value=value, k=k)
    elif field and value:
        results = filter_search(field, value, k=k)
    elif query:
        results = semantic_search(query, k=k)
    else:
        console.print("[red]Provide a query and/or --field/--value.[/red]")
        raise typer.Exit(1)
    _print_results(results)


@app.command()
def chat() -> None:
    """Interactive CLI chat over the dataset. The agent searches via tools —
    it never gets the full dataset dumped into its prompt."""
    _require_db_or_exit()
    llm = build_llm()
    history = initial_history()
    console.print("[bold]CV Screener chat.[/bold] Ask about the candidates. Type 'exit' to quit.\n")
    while True:
        try:
            user_input = typer.prompt(">")
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if user_input.strip().lower() in {"exit", "quit"}:
            break
        if not user_input.strip():
            continue
        answer, history = run_turn(llm, history, user_input)
        console.print(f"\n{answer}\n")


if __name__ == "__main__":
    app()
