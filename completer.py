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
    "help",
    "exit",
    "shell"
]

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
        text = document.text_before_cursor.strip()
        parts = text.split()

        # First word → commands
        if len(parts) <= 1:
            prefix = parts[0] if parts else ""
            for cmd in COMMANDS:
                if cmd.startswith(prefix):
                    yield Completion(cmd, start_position=-len(prefix))
            return

        # Second word → project names
        if parts[0] in {"start", "open", "desc", "folder"}:
            projects = self.get_project_names()
            last = parts[-1]

            for p in projects:
                if p.lower().startswith(last.lower()):
                    yield Completion(p, start_position=-len(last))


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
            args = shlex.split(user_input)
            cli.main(args=args, prog_name="projects", standalone_mode=False)
        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            click.echo(f"Error: {e}")
