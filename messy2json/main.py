#!/usr/bin/env python3
"""
messy2json
----------
Global CLI tool. Paste any messy text — email, meeting notes, voice-to-text —
and get back strict JSON: {summary, action_items, deadline}

Usage (after pip install .):
    messy2json                   # interactive loop
    messy2json -f notes.txt      # read from file
    cat notes.txt | messy2json   # pipe input
    messy2json -f notes.txt -o out.json   # save result to file

API key is safely stored in the platform-appropriate system config directory.
Override anytime by setting the GROQ_API_KEY environment variable.
"""

import argparse
import json
import os
import pathlib
import sys
import time

from groq import Groq
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

console = Console()

# ── config paths (Cross-Platform Compliant) ──────────────────────────────────
if os.name == "nt":  # Windows
    CONFIG_DIR = pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home())) / "messy2json"
else:  # macOS / Linux
    CONFIG_DIR = pathlib.Path.home() / ".config" / "messy2json"

CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_ATTEMPTS  = 3
REQUIRED_KEYS = {"summary", "action_items", "deadline"}

SYSTEM_PROMPT = """You are a strict information-extraction engine.

You will be given raw, possibly messy text: an email, meeting notes, or a rambling
voice-to-text transcript. It may contain typos, filler words, run-on sentences, or
no clear structure at all.

Extract exactly this JSON object and return NOTHING else - no markdown fences, no
commentary, no preamble, no explanation:

{
  "summary": "one to three sentence plain-English summary of what the text is about",
  "action_items": ["short actionable task", "another task"],
  "deadline": "the deadline mentioned in the text (in its own words), or null if none is mentioned"
}

Rules:
- Output ONLY that JSON object.
- "action_items" is always a JSON array of strings. Use [] if there are none.
- "deadline" is always a JSON string or JSON null. Never omit the key, never use "N/A" or "".
- Never add any key other than summary, action_items, deadline.
- Even if the text is garbled, very short, or nearly empty, still return the full
  JSON object with your best-effort summary and empty/null values where nothing
  was found. Do not refuse and do not error out.
"""


# ── config manager ────────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text())
    except Exception:
        return {}


def _save_config(data: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def _first_time_setup() -> str:
    console.print()
    console.print(
        Panel(
            "No API key found.\n\n"
            "Get a free key at [bold cyan]https://console.groq.com[/bold cyan]\n"
            "[dim](no credit card needed — sign up and click API Keys)[/dim]\n\n"
            "Your key will be securely saved to your local system configuration\n"
            "directory and never asked again.",
            title="[bold yellow]⚙  First Time Setup[/bold yellow]",
            border_style="yellow",
            expand=False,
        )
    )
    
    while True:
        try:
            key = input("\n  Enter your Groq API key: ").strip()
        except KeyboardInterrupt:
            console.print("\n[dim]Setup cancelled.[/dim]")
            sys.exit(0)

        if not key:
            console.print("[bold red]✗[/bold red] No key entered. Please try again or press Ctrl+C to exit.")
            continue

        # Live authentication check over the network before committing to disk
        with console.status("[bold yellow]Validating API key with Groq...[/bold yellow]", spinner="dots"):
            try:
                test_client = Groq(api_key=key)
                test_client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                )
                break  # Validation passed! Exit the authentication loop
            except Exception as e:
                console.print(f"\n[bold red]✗[/bold red] Authentication failed! The API key is invalid.")
                console.print(f"[dim]Groq API Error: {e}[/dim]")
                console.print("[bold yellow] Please double-check your key and try again.[/bold yellow]\n")

    _save_config({"api_key": key, "model": DEFAULT_MODEL})
    console.print("[bold green]✓[/bold green] Key verified and saved successfully!\n")
    return key


def get_api_key() -> str:
    """Priority: env var → config file → first-time setup prompt."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return key

    key = _load_config().get("api_key", "").strip()
    if key:
        return key

    return _first_time_setup()


def get_model() -> str:
    """Read model from config file, fall back to default."""
    env_model = os.environ.get("GROQ_MODEL", "").strip()
    if env_model:
        return env_model
    return _load_config().get("model", DEFAULT_MODEL)


# ── core extraction ───────────────────────────────────────────────────────────

def _safe_fallback(reason: str) -> dict:
    return {
        "summary": f"Could not process input: {reason}",
        "action_items": [],
        "deadline": None,
    }


def _validate(data) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "top-level JSON is not an object"
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        return False, f"missing keys: {sorted(missing)}"
    if not isinstance(data["summary"], str):
        return False, "'summary' must be a string"
    if not isinstance(data["action_items"], list) or not all(
        isinstance(x, str) for x in data["action_items"]
    ):
        return False, "'action_items' must be a list of strings"
    if data["deadline"] is not None and not isinstance(data["deadline"], str):
        return False, "'deadline' must be a string or null"
    return True, ""


def extract_json(raw_text: str, client: Groq, model: str) -> dict:
    if not raw_text or not raw_text.strip():
        return _safe_fallback("empty input")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": raw_text},
    ]

    last_error = "unknown error"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=1024,
            )
            content = response.choices[0].message.content

            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                last_error = f"invalid JSON syntax ({e})"
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": (
                        f"That was not valid JSON ({e}). Reply again with ONLY the "
                        "corrected JSON object, no other text."
                    ),
                })
                continue

            ok, err = _validate(data)
            if ok:
                return {k: data[k] for k in REQUIRED_KEYS}

            last_error = f"schema mismatch ({err})"
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": (
                    f"That JSON didn't match the required schema ({err}). Reply again "
                    "with ONLY the corrected JSON object, no other text."
                ),
            })

        except Exception as e:
            last_error = str(e)
            if attempt < MAX_ATTEMPTS:
                time.sleep(1.5 * attempt)

    return _safe_fallback(last_error)


# ── UI helpers ────────────────────────────────────────────────────────────────

def show_banner(model: str):
    console.print()
    console.print(
        Panel(
            "[bold]messy2json[/bold]\n"
            "Paste any messy text — email, meeting notes, voice-to-text — "
            "and get back structured JSON.\n\n"
            f"[dim]Model  :[/dim] [yellow]{model}[/yellow]\n"
            "[dim]Output :[/dim] [cyan]summary[/cyan]  [cyan]action_items[/cyan]  [cyan]deadline[/cyan]\n"
            "[dim]GitHub :[/dim] [bold link=https://github.com/hamzatahir06/Messy2JSON]https://github.com/hamzatahir06/Messy2JSON[/bold link]",
            title="[bold green]🤖 Agent Ready[/bold green]",
            border_style="green",
            expand=False,
        )
    )
    console.print(
        "  [dim]HOW TO USE[/dim]\n"
        "  • Type [bold cyan]/do[/bold cyan] on a new line and press Enter to extract JSON\n"
        "  • Press [bold red]Ctrl+C[/bold red] at any time to exit\n"
    )

def _read_one_input() -> str:
    console.print("[dim]─────────────────────────────────────[/dim]")
    console.print("[dim]Paste your text below (or Ctrl+C to stop):[/dim]\n")
    lines = []
    while True:
        try:
            line = input()
        except KeyboardInterrupt:
            console.print("\n\n[bold green]Agent signing off.[/bold green] Goodbye!\n")
            sys.exit(0)
            
        if line.strip() == "/do":
            break
        lines.append(line)
    return "\n".join(lines)


def _print_result(output_str: str, is_error: bool, output_file: str | None):
    console.print()
    if is_error:
        console.print("[bold red]✗ Something went wrong[/bold red]")
    else:
        console.print("[bold green]✓ Extracted JSON[/bold green]")

    console.print(Syntax(output_str, "json", theme="ansi_dark", word_wrap=True))

    if CLIPBOARD_AVAILABLE and not is_error:
        try:
            pyperclip.copy(output_str)
            console.print("[dim]✓ Copied to clipboard[/dim]")
        except Exception:
            console.print("[dim]⚠ Clipboard unavailable on this system[/dim]")

    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output_str)
            console.print(f"[dim]✓ Saved to {output_file}[/dim]")
        except Exception as e:
            console.print(f"[bold red]✗ Failed to save output file:[/bold red] {e}")


def _execute_processing_pipeline(raw_text: str, client: Groq, model: str, output_file: str | None, status_msg: str):
    """Centralized extraction engine to prevent code repetition."""
    with console.status(status_msg, spinner="dots"):
        result = extract_json(raw_text, client, model=model)
        
    output_str = json.dumps(result, indent=2, ensure_ascii=False)
    is_error = result["summary"].startswith("Could not process input:")
    _print_result(output_str, is_error, output_file)


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="messy2json",
        description="Turn messy text into strict JSON.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    parser.add_argument("-f", "--file",   help="read from a file instead of interactive mode")
    parser.add_argument("-o", "--output", help="also save the JSON result to this file")
    parser.add_argument("--model",        help=f"override Groq model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    api_key = get_api_key()
    model   = args.model or get_model()
    client  = Groq(api_key=api_key)

    # ── non-interactive mode (Files / Streams) ────────────────────────────────
    if args.file or not sys.stdin.isatty():
        if args.file:
            try:
                raw_text = open(args.file, encoding="utf-8").read()
            except FileNotFoundError:
                console.print(f"[bold red]✗ Error:[/bold red] The file '{args.file}' could not be found.")
                sys.exit(1)
            except Exception as e:
                console.print(f"[bold red]✗ Error reading file:[/bold red] {e}")
                sys.exit(1)
        else:
            raw_text = sys.stdin.read()

        _execute_processing_pipeline(
            raw_text, client, model, args.output, "[bold yellow]Processing input data...[/bold yellow]"
        )
        return

    # ── interactive loop mode ─────────────────────────────────────────────────
    show_banner(model)
    try:
        while True:
            raw_text = _read_one_input()
            if not raw_text.strip():
                console.print("[dim]⚠  No text entered — paste something and type /do[/dim]\n")
                continue

            _execute_processing_pipeline(
                raw_text, client, model, args.output, "[bold yellow]  Processing...[/bold yellow]"
            )
            console.print()

    except KeyboardInterrupt:
        console.print("\n\n[bold green]Agent signing off.[/bold green] Goodbye!\n")


if __name__ == "__main__":
    main()