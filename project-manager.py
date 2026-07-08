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

    # Support legacy "desc_" field — prefer "description" if it exists
    metadata["description"] = metadata.get("description") or metadata.get("desc_") or ""
    # Remove legacy field if present (migration script handles bulk cleanup)
    metadata.pop("desc_", None)
    metadata["programming_language"] = metadata.get("programming_language") or "unknown"
    metadata["project_status"] = metadata.get("project_status") or "unknown"
    metadata["tag"] = (metadata.get("tag") or DEFAULT_TAG).strip().lower()
    # language_version is optional — None means "use default"
    metadata["language_version"] = metadata.get("language_version") or None
    return metadata


def save_metadata(project_folder, metadata):
    """Write metadata back to metadata.json."""
    meta_file = project_folder / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)


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


def build_run_command(language, language_version, main_file_path, project_folder):
    """
    Build the appropriate run command based on language and optional version.
    Returns a list of command arguments for subprocess.run().
    """
    if language == "python":
        if language_version:
            # Try versioned Python executable (e.g. python3.10, python3.12)
            versioned = f"python{language_version}"
            return [versioned, str(main_file_path)]
        return [sys.executable, str(main_file_path)]

    elif language == "javascript":
        if language_version:
            # Try versioned Node (e.g. node18, node20)
            versioned = f"node{language_version}"
            return [versioned, str(main_file_path)]
        return ["node", str(main_file_path)]

    elif language == "c":
        exe_path = project_folder / "main.exe"
        if language_version:
            # Try versioned GCC (e.g. gcc-12, gcc-13)
            versioned = f"gcc-{language_version}"
            return [versioned, str(main_file_path), "-o", str(exe_path)], [str(exe_path)]
        return ["gcc", str(main_file_path), "-o", str(exe_path)], [str(exe_path)]

    else:
        return None


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
                    version = metadata.get("language_version") if metadata else None
                    if version:
                        click.echo(f" - {name} [{language} {version}]")
                    else:
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
        language_version = metadata.get("language_version") if metadata else None

        if language == "python":
            cmd = build_run_command(language, language_version, main_file_path, project_folder)
            subprocess.run(cmd, check=True)

        elif language == "javascript":
            cmd = build_run_command(language, language_version, main_file_path, project_folder)
            subprocess.run(cmd, check=True)

        elif language == "c":
            compile_cmd, run_cmd = build_run_command(language, language_version, main_file_path, project_folder)
            subprocess.run(compile_cmd, check=True)
            subprocess.run(run_cmd, check=True)

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
    version = metadata.get("language_version")
    if version:
        click.echo(f"Version              : {version}")
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
@click.argument("project_name", nargs=-1)
@click.option("--set", "lang_version", default=None, help="Set the language version (e.g. 3.10, 18, 12)")
def version(project_name, lang_version):
    """Show or set the language version for a project.

    Examples:

      projects version my project              Show current version

      projects version my project --set 3.10   Set Python version to 3.10
    """
    project_name_str, project_folder = get_project_folder(project_name)
    if not project_folder:
        return

    metadata = load_metadata(project_folder)
    if not metadata:
        click.echo(f"No readable metadata.json found in {project_name_str}.")
        return

    if lang_version:
        # Set the version
        metadata["language_version"] = lang_version
        save_metadata(project_folder, metadata)
        language = metadata.get("programming_language", "unknown")
        click.echo(f"Set {project_name_str} ({language}) version to {lang_version}.")
    else:
        # Show the current version
        current = metadata.get("language_version")
        if current:
            click.echo(f"{project_name_str} language version: {current}")
        else:
            click.echo(f"{project_name_str} has no specific language version set (uses system default).")


@cli.command()
@click.argument("project_name", nargs=-1)
@click.argument("new_name", nargs=-1)
def rename(project_name, new_name):
    """Rename a project folder.

    Examples:

      projects rename "My Project" "My Awesome Project"
    """
    project_name_str, project_folder = get_project_folder(project_name)
    if not project_folder:
        return

    new_name_str = format_project_name(new_name)
    if not new_name_str:
        click.echo("Please specify a new name.")
        return

    new_folder = PROJECT_PATH / new_name_str
    if new_folder.exists():
        click.echo(f"A project named '{new_name_str}' already exists.")
        return

    # Rename the folder
    project_folder.rename(new_folder)
    click.echo(f"Renamed '{project_name_str}' to '{new_name_str}'.")


@cli.command()
@click.argument("project_name", nargs=-1)
@click.option("--set", "new_tag", default=None, help="Set the tag for a project (e.g. tools, game, web)")
def tag(project_name, new_tag):
    """Show or set the tag for a project.

    Examples:

      projects tag my project              Show current tag

      projects tag my project --set game   Set tag to 'game'
    """
    project_name_str, project_folder = get_project_folder(project_name)
    if not project_folder:
        return

    metadata = load_metadata(project_folder)
    if not metadata:
        click.echo(f"No readable metadata.json found in {project_name_str}.")
        return

    if new_tag:
        # Set the tag
        metadata["tag"] = new_tag.strip().lower()
        save_metadata(project_folder, metadata)
        click.echo(f"Set tag for '{project_name_str}' to '{new_tag.strip().lower()}'.")
    else:
        # Show the current tag
        current = metadata.get("tag", DEFAULT_TAG)
        click.echo(f"Tag for '{project_name_str}': {current}")


@cli.command()
@click.argument("query", nargs=-1)
def search(query):
    """Search projects by name, language, tag, or description.

    Examples:

      projects search python

      projects search game

      projects search my cool project
    """
    query_str = format_project_name(query)
    if not query_str:
        click.echo("Please specify a search query.")
        return

    query_lower = query_str.lower()
    results = []

    try:
        for entry in PROJECT_PATH.iterdir():
            if entry.is_dir() and entry.name.lower() != CODE_FOLDER_NAME.lower():
                name = entry.name
                metadata = load_metadata(entry)

                # Search in name
                if query_lower in name.lower():
                    results.append((name, metadata))
                    continue

                if metadata:
                    # Search in language
                    if query_lower in metadata.get("programming_language", "").lower():
                        results.append((name, metadata))
                        continue

                    # Search in tag
                    if query_lower in metadata.get("tag", "").lower():
                        results.append((name, metadata))
                        continue

                    # Search in description
                    if query_lower in metadata.get("description", "").lower():
                        results.append((name, metadata))
                        continue

    except FileNotFoundError:
        click.echo(f"Project path not found: {PROJECT_PATH}")
        return

    if results:
        click.echo(f"\nFound {len(results)} project(s) matching '{query_str}':\n")
        for name, metadata in sorted(results, key=lambda x: x[0].lower()):
            language = metadata.get("programming_language", "unknown") if metadata else "unknown"
            tag = metadata.get("tag", DEFAULT_TAG) if metadata else DEFAULT_TAG
            click.echo(f"  {name}  [{language}]  ({tag})")
        click.echo()
    else:
        click.echo(f"No projects found matching '{query_str}'.")


@cli.command()
@click.argument("project_name", nargs=-1)
def stats(project_name):
    """Show project statistics: file count, folder size, last modified, etc.

    Examples:

      projects stats my project
    """
    project_name_str, project_folder = get_project_folder(project_name)
    if not project_folder:
        return

    metadata = load_metadata(project_folder)

    # Count files and calculate total size
    total_files = 0
    total_size = 0
    last_modified = 0

    for item in project_folder.rglob("*"):
        if item.is_file():
            total_files += 1
            try:
                total_size += item.stat().st_size
                mtime = item.stat().st_mtime
                if mtime > last_modified:
                    last_modified = mtime
            except OSError:
                pass

    # Format size
    if total_size < 1024:
        size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.1f} KB"
    else:
        size_str = f"{total_size / (1024 * 1024):.2f} MB"

    # Format last modified time
    from datetime import datetime
    last_mod_str = datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M:%S") if last_modified else "N/A"

    # Get entry point from main.txt
    main_txt = project_folder / "main.txt"
    entry_point = "N/A"
    if main_txt.is_file():
        entry_point = main_txt.read_text(encoding="utf-8").strip()

    click.echo("\n====================================")
    click.echo("          PROJECT STATS")
    click.echo("====================================\n")

    click.echo(f"Name              : {project_name_str}")
    click.echo(f"Folder size       : {size_str}")
    click.echo(f"Total files       : {total_files}")
    click.echo(f"Last modified     : {last_mod_str}")
    click.echo(f"Entry point       : {entry_point}")

    if metadata:
        click.echo(f"Language          : {metadata.get('programming_language', 'unknown')}")
        version = metadata.get("language_version")
        if version:
            click.echo(f"Version           : {version}")
        click.echo(f"Status            : {metadata.get('project_status', 'unknown')}")
        click.echo(f"Tag               : {metadata.get('tag', DEFAULT_TAG)}")

    click.echo("\n====================================\n")


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

    click.echo("  version <name> [--set version]")
    click.echo("      Show or set the language version for a project.\n")

    click.echo("  rename <name> <new name>")
    click.echo("      Rename a project folder.\n")

    click.echo("  tag <name> [--set tag]")
    click.echo("      Show or set the tag for a project.\n")

    click.echo("  search <query>")
    click.echo("      Search projects by name, language, tag, or description.\n")

    click.echo("  stats <name>")
    click.echo("      Show project statistics (file count, size, last modified).\n")

    click.echo("Examples:")
    click.echo("  projects create My API")
    click.echo("  projects create Discord Bot --lang javascript")
    click.echo("  projects create Game Engine --lang c")
    click.echo("  projects start Discord Bot")
    click.echo("  projects desc Game Engine")
    click.echo("  projects version Game Engine")
    click.echo("  projects version Game Engine --set 3.10")
    click.echo("  projects rename Game Engine Game Engine 2")
    click.echo("  projects tag Game Engine --set game")
    click.echo("  projects search python\n")


try:
    from completer import interactive_shell

    @cli.command()
    def shell():
        """Start interactive prompt toolkit shell with autocomplete."""
        interactive_shell(cli)

except Exception as e:
    print(f"completer import failed: {e}")

if __name__ == "__main__":
    cli()
