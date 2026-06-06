# Projects CLI

A small command-line helper for creating, opening, describing, listing, and running local projects.

The tool treats each folder beside `projects_code` as a project. Each project can include:

- `main.py`: the default starter Python file
- `main.txt`: the file to run when using `start`
- `metadata.json`: project language, status, tag, and description

## Commands

```powershell
projects list
projects list --show-language
projects create my project
projects create my project --lang javascript
projects create my project --lang c
projects open my project
projects folder
projects folder my project
projects start my project
projects desc my project
projects shell
projects help
```

### Command Overview

| Command | Description |
|---|---|
| `list` | List all projects grouped by tag |
| `list --show-language` | List projects with their programming language |
| `create <name>` | Create a new project from a language template (default: python) |
| `create <name> --lang` | Create a project with a specific language: `python`, `javascript`, or `c` |
| `start <name>` | Run the project's entry file (supports Python, Node.js, and C) |
| `open <name>` | Open a project in VS Code |
| `folder` | Open the projects root folder in file explorer |
| `folder <name>` | Open a specific project folder in file explorer |
| `desc <name>` | Show project metadata (language, status, tag, description) |
| `shell` | Start an interactive shell with tab-completion |
| `help` | Show command overview |

## Interactive Shell

Running `projects shell` starts an interactive prompt with tab-completion:

```
Projects CLI Shell (type 'exit' to quit)

projects> 
```

- **Tab** autocompletes commands and project names
- Project names with spaces are supported (type the first few letters and press Tab)
- Type `exit` or `quit` to leave the shell, or press `Ctrl+C`

## Metadata

Each project can be grouped and described with `metadata.json`:

```json
{
  "programming_language": "python",
  "description": "Short description of what this project does.",
  "project_status": "under development",
  "tag": "tools"
}
```

`tag` groups projects in `projects list`. `description` is shown by `projects desc <name>`. Supported languages for `start`: `python`, `javascript`, `c`.

## File Structure

```
projects/
├── projects_code/
│   ├── project.py       # CLI entry point
│   ├── completer.py     # Interactive shell and tab-completion
│   └── templates/
│       ├── python/
│       ├── javascript/
│       └── c/
├── My Project/
│   ├── main.py
│   ├── main.txt
│   └── metadata.json
└── Another Project/
    └── ...
```

## Setup

Add `projects_code` to your PATH and run commands as:

```powershell
projects <command> <project name>
```

Or run directly with Python:

```powershell
python project.py <command> <project name>
```
