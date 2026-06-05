# Projects CLI

A small command-line helper for creating, opening, describing, listing, and running local projects.

The tool treats each folder beside `projects_code` as a project. Each project can include:

- `main.py`: the default starter Python file
- `main.txt`: the file to run when using `start`
- `metadata.json`: project language, status, tag, and description

## Commands

```powershell
projects list
projects create my project
projects open my project
projects folder my project
projects start my project
projects desc my project
```

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

`tag` is used by `projects list` to group projects. `description` is shown by `projects desc <name>`.

## Setup

Run commands through `projects.bat`, or add this folder to your PATH and use:

```powershell
projects <command> <project name>
```
