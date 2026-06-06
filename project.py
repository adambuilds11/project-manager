import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import click


PROJECT_PATH = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates"
CODE_FOLDER_NAME = Path(__file__).resolve().parent.name
DEFAULT_TAG = "untagged"
REQUIRED_TEMPLATE_FILES = ("main.txt", "metadata.json")


def format_project_name(project_name):
    """Convert Click's multi-word argument tuple into one project name."""
    return " ".join(project_name).strip()


def get_project_folder(project_name):
    """Return the project name and folder, or print help when no name is given."""
    project_name_str = format_project_name(project_name)

    if not project_name_str:
        click.echo("Please specify a project name.")
        list_projects()
        return None, None

    project_folder = PROJECT_PATH / project_name_str
    if not project_folder.exists():
        click.echo(f"Project not found: {project_name_str}")
        return None, None

    return project_name_str, project_folder


def load_metadata(project_folder):
    """Load project metadata and keep older desc_ files compatible."""
    meta_file = project_folder / "metadata.json"

    if not meta_file.is_file():
        return None

    try:
        metadata = json.loads(meta_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        click.echo(f"Invalid metadata.json in {project_folder.name}.")
        return None

    metadata["description"] = metadata.get("description") or metadata.get("desc_") or ""
    metadata["programming_language"] = metadata.get("programming_language") or "unknown"
    metadata["project_status"] = metadata.get("project_status") or "unknown"
    metadata["tag"] = (metadata.get("tag") or DEFAULT_TAG).strip().lower()
    return metadata


def open_with_system(path):
    """Open a file or folder using the current operating system."""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def open_in_vscode(project_folder, project_name):
    command = ["code", str(project_folder)]

    main_txt = project_folder / "main.txt"

    if main_txt.exists():
        entry_file = project_folder / main_txt.read_text(
            encoding="utf-8"
        ).strip()

        if entry_file.exists():
            command.extend(["-g", str(entry_file)])

    try:
        subprocess.run(command, shell=True, check=True)
        click.echo(f"Opened '{project_name}' in VS Code.")
    except (subprocess.SubprocessError, OSError) as error:
        click.echo(f"Could not open VS Code: {error}")


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Manage, open, describe, and run local project folders."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_projects)


@cli.command(name="list")
@click.option(
    "--show-language",
    is_flag=True,
    help="Display programming language for each project."
)
def list_projects(show_language):
    """List projects grouped by metadata tag."""
    click.echo("\nYour Projects:\n------------------")

    projects_by_tag = {}

    try:
        for entry in PROJECT_PATH.iterdir():
            if entry.is_dir() and entry.name.lower() != CODE_FOLDER_NAME.lower():
                metadata = load_metadata(entry)
                tag = metadata["tag"] if metadata else DEFAULT_TAG
                projects_by_tag.setdefault(tag, []).append(entry.name)

        for tag in sorted(projects_by_tag):

            click.echo(f"\n{tag.upper()} PROJECTS:")

            for name in sorted(projects_by_tag[tag]):

                if show_language:
                    metadata = load_metadata(PROJECT_PATH / name)

                    language = (
                        metadata.get("programming_language", "unknown")
                        if metadata
                        else "unknown"
                    )

                    click.echo(f" - {name} [{language}]")

                else:
                    click.echo(f" - {name}")

    except FileNotFoundError:
        click.echo(f"Project path not found: {PROJECT_PATH}")


@cli.command()
@click.argument("project_name", nargs=-1)
def start(project_name):
    """Run the file listed in a project's main.txt."""
    project_name_str, project_folder = get_project_folder(project_name)
    if not project_folder:
        return

    main_txt = project_folder / "main.txt"
    if not main_txt.is_file():
        click.echo(f"No main.txt found in {project_name_str}; cannot run project.")
        return

    main_file = main_txt.read_text(encoding="utf-8").strip()
    main_file_path = project_folder / main_file

    if not main_file_path.is_file():
        click.echo(f"Main file specified in main.txt not found: {main_file}")
        return

    click.echo(f"Running {main_file}...\n")

    try:
        metadata = load_metadata(project_folder)

        language = (
            metadata.get("programming_language", "python").lower()
            if metadata
            else "python"
        )

        if language == "python":
            subprocess.run(
                [sys.executable, str(main_file_path)],
                check=True
            )

        elif language == "javascript":
            subprocess.run(
                ["node", str(main_file_path)],
                check=True
            )

        elif language == "c":
            exe_path = project_folder / "program.exe"

            subprocess.run(
                [
                    "gcc",
                    str(main_file_path),
                    "-o",
                    str(exe_path)
                ],
                check=True
            )

            subprocess.run(
                [str(exe_path)],
                check=True
            )

        else:
            open_with_system(main_file_path)
    except (subprocess.SubprocessError, OSError) as error:
        click.echo(f"Error running file: {error}")


@cli.command()
@click.argument("project_name", nargs=-1)
def desc(project_name):
    """Show a project's language, status, tag, and description."""
    project_name_str, project_folder = get_project_folder(project_name)
    if not project_folder:
        return

    metadata = load_metadata(project_folder)
    if not metadata:
        click.echo(f"No readable metadata.json found in {project_name_str}; cannot describe project.")
        return

    click.echo("\n====================================")
    click.echo("            PROJECT INFO")
    click.echo("====================================\n")

    click.echo(f"Name                 : {project_name_str}")
    click.echo(f"Programming Language : {metadata['programming_language']}")
    click.echo(f"Status               : {metadata['project_status']}")
    click.echo(f"Tag                  : {metadata['tag']}")
    click.echo("Description          :")
    click.echo(f"  {metadata['description'] or 'No description yet.'}")

    click.echo("\n====================================\n")


@cli.command()
@click.argument("project_name", nargs=-1)
@click.option(
    "--lang",
    default="python",
    type=click.Choice(["python", "javascript", "c"]),
    help="Project language."
)
def create(project_name, lang):
    """Create a project from templates, then open it in VS Code."""
    project_name_str = format_project_name(project_name)
    if not project_name_str:
        click.echo("Please specify a project name.")
        return

    project_folder = PROJECT_PATH / project_name_str
    template_lang_folder = TEMPLATE_PATH / lang

    if not template_lang_folder.exists():
        click.echo(f"Template not found: {lang}")
        return

    if not project_folder.exists():
        shutil.copytree(template_lang_folder, project_folder)
        click.echo(f"Project '{project_name_str}' created at {project_folder}.")
    else:
        click.echo(f"Project '{project_name_str}' already exists. Checking required files...")
        for filename in REQUIRED_TEMPLATE_FILES:
            target_file = project_folder / filename
            template_file = template_lang_folder / filename
            if not target_file.exists():
                if template_file.exists():
                    shutil.copy(template_file, target_file)
                    click.echo(f"Created missing file: {filename}")
                else:
                    click.echo(f"Warning: template {filename} not found; cannot create it.")

    open_in_vscode(project_folder, project_name_str)


@cli.command("open")
@click.argument("project_name", nargs=-1)
def open_projects(project_name):
    """Open a project in VS Code."""
    project_name_str, project_folder = get_project_folder(project_name)
    if not project_folder:
        return

    open_in_vscode(project_folder, project_name_str)


@cli.command("folder")
@click.argument("project_name", nargs=-1)
def open_projects_folder(project_name):
    """Open the projects folder or a project folder in file explorer."""
    if not project_name:
        target_path = PROJECT_PATH
    else:
        project_name_str = format_project_name(project_name)
        target_path = PROJECT_PATH / project_name_str

        if not target_path.exists():
            click.echo(f"Project not found: {project_name_str}")
            return

    try:
        open_with_system(target_path)
        click.echo(f"Opened: {target_path}")
    except (subprocess.SubprocessError, OSError) as error:
        click.echo(f"Error opening folder: {error}")


@cli.command()
def help():
    """Show the custom command overview."""

    click.echo("\n==============================")
    click.echo("        PROJECTS CLI")
    click.echo("==============================\n")

    click.echo("Commands:")
    click.echo("  list")
    click.echo("      List all projects grouped by tag.\n")

    click.echo("  create <name> [--lang python|javascript|c]")
    click.echo("      Create a new project from a language template.")
    click.echo("      Default language: python\n")

    click.echo("  start <name>")
    click.echo("      Run the project's entry file.")
    click.echo("      Supports Python, JavaScript (Node.js), and C.\n")

    click.echo("  open <name>")
    click.echo("      Open a project in VS Code.\n")

    click.echo("  folder [name]")
    click.echo("      Open the projects folder or a project folder.\n")

    click.echo("  desc <name>")
    click.echo("      Show project metadata.\n")

    click.echo("Examples:")
    click.echo("  projects create My API")
    click.echo("  projects create Discord Bot --lang javascript")
    click.echo("  projects create Game Engine --lang c")
    click.echo("  projects start Discord Bot")
    click.echo("  projects desc Game Engine\n")


if __name__ == "__main__":
    cli()
