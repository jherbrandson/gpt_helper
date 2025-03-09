import os

def custom_tree(directory, prefix="", level=1, max_level=4):
    """
    Recursively builds a tree-like list of strings for the given directory,
    similar to the Unix 'tree' command.
    
    Directories in the ignore set are skipped.
    Files starting with '.' are skipped unless they are in ENABLE_FILES.
    """
    # Updated ignore set to include "build"
    IGNORE_DIRS = {"migrations", "__pycache__", ".git", "node_modules", ".next", "public", "venv", "migration_backups", ".pytest_cache", "build"}
    ENABLE_FILES = {".env", ".env.local"}
    result_lines = []
    if level > max_level:
        return result_lines
    try:
        entries = sorted(os.listdir(directory))
    except Exception:
        return result_lines
    allowed_hidden = {name.lower() for name in ENABLE_FILES}
    entries_filtered = []
    for entry in entries:
        full_path = os.path.join(directory, entry)
        if os.path.isdir(full_path):
            if entry in IGNORE_DIRS:
                continue
            entries_filtered.append(entry)
        else:
            if entry.startswith('.') and entry.lower() not in allowed_hidden:
                continue
            entries_filtered.append(entry)
    count = len(entries_filtered)
    for i, entry in enumerate(entries_filtered):
        full_path = os.path.join(directory, entry)
        connector = "├── " if i < count - 1 else "└── "
        result_lines.append(prefix + connector + entry)
        if os.path.isdir(full_path):
            extension = "│   " if i < count - 1 else "    "
            result_lines.extend(custom_tree(full_path, prefix + extension, level + 1, max_level))
    return result_lines
