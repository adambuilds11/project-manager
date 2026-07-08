from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
import shlex
import click
from pathlib import Path

PROJECT_PATH = Path(__file__).resolve().parent.parent
CODE_FOLDER_NAME = Path(__file__).resolve().parent.name

COMMANDS = [
    "list",
    "create",
    "start",
    "open",
    "folder",
    "desc",
    "version",
    "rename",
    "tag",
    "search",
    "stats",
    "help",
    "exit",
    "shell"
]

LANGUAGE_OPTIONS = ["python", "javascript", "c"]

# Commands that take a project name as the next argument
PROJECT_NAME_COMMANDS = {"start", "open", "desc", "folder", "create", "version", "rename", "tag", "stats"}


class ProjectsCompleter(Completer):
    def get_project_names(self):
        try:
            return [
                p.name
                for p in PROJECT_PATH.iterdir()
                if p.is_dir() and p.name.lower() != CODE_FOLDER_NAME.lower()
            ]
        except FileNotFoundError:
            return []

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        # Don't strip — we need to know about trailing spaces
        stripped = text.lstrip()
        parts = shlex.split(stripped) if stripped else []

        # --- First word → commands ---
        if not parts:
            for cmd in COMMANDS:
                yield Completion(cmd, start_position=0)
            return

        # If we're still typing the first word (no space after it)
        if len(parts) == 1 and not text.endswith(" "):
            prefix = parts[0]
            for cmd in COMMANDS:
                if cmd.startswith(prefix):
                    yield Completion(cmd, start_position=-len(prefix))
            return

        first_word = parts[0].lower()

        # --- Second word → project names (for commands that take a project) ---
        if first_word in PROJECT_NAME_COMMANDS:
            # Check if we're completing a --lang flag value
            if first_word == "create" and len(parts) >= 3 and parts[-2] == "--lang":
                prefix = parts[-1]
                for lang in LANGUAGE_OPTIONS:
                    if lang.startswith(prefix):
                        yield Completion(lang, start_position=-len(prefix))
                return

            # Check if we're completing the --lang flag itself
            if first_word == "create" and len(parts) >= 2:
                last = parts[-1]
                if "--lang".startswith(last) and "--lang" not in parts:
                    yield Completion("--lang", start_position=-len(last))
                    return

            # Complete project names
            projects = self.get_project_names()
            last = parts[-1]

            for p in projects:
                if p.lower().startswith(last.lower()):
                    yield Completion(p, start_position=-len(last))

        # --- --lang flag completion for create (when typed after project name) ---
        if first_word == "create" and len(parts) >= 2:
            last = parts[-1]
            if "--lang".startswith(last) and "--lang" not in parts:
                yield Completion("--lang", start_position=-len(last))


def interactive_shell(cli):
    session = PromptSession(completer=ProjectsCompleter())
    click.echo("Projects CLI Shell (type 'exit' to quit)\n")
    while True:
        try:
            user_input = session.prompt("projects> ").strip()
            if not user_input:
                continue
            if user_input in {"exit", "quit"}:
                break
            # Block shell-in-a-shell
            if user_input.strip().lower() == "shell":
                click.echo("Already in the shell!\n")
                continue
            args = shlex.split(user_input)
            cli.main(args=args, prog_name="projects", standalone_mode=False)
            # Add spacing after command output so the next prompt isn't cramped
            click.echo()
        except (KeyboardInterrupt, EOFError):
            break
        except SystemExit:
            # Click might try to sys.exit() — don't let it kill the shell
            click.echo()
        except Exception as e:
            click.echo(f"Error: {e}")
            click.echo()
