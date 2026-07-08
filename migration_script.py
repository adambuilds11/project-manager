"""
Migration script: ensures every project's metadata.json has all required fields
with sensible defaults, so load_metadata() in project-manager.py works correctly.
"""
import json
from pathlib import Path

PROJECTS_DIR = Path(__file__).resolve().parent.parent

# The fields that load_metadata() expects, with their defaults
REQUIRED_FIELDS = {
    "programming_language": "unknown",
    "description": "",
    "project_status": "unknown",
    "tag": "untagged",
    "language_version": "",
}

# Fields that are no longer used (will be removed if present)
DEPRECATED_FIELDS = {"runtime", "desc_"}

updated = 0

for project in PROJECTS_DIR.iterdir():
    if not project.is_dir():
        continue

    # Skip the projects_code folder itself
    if project.name.lower() == Path(__file__).resolve().parent.name.lower():
        continue

    metadata_file = project / "metadata.json"

    if not metadata_file.exists():
        continue

    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        changed = False

        # Add any missing required fields with defaults
        for field, default in REQUIRED_FIELDS.items():
            if field not in metadata or metadata[field] is None:
                metadata[field] = default
                changed = True

        # Remove deprecated fields
        for field in DEPRECATED_FIELDS:
            if field in metadata:
                del metadata[field]
                changed = True

        if changed:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
            updated += 1
            print(f"Updated: {project.name}")

    except Exception as e:
        print(f"Failed: {project.name} -> {e}")

print(f"\nDone. Updated {updated} projects.")
