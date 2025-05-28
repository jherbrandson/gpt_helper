# gpt_helper/dev/steps.py
import os
import subprocess
import tempfile
from setup.constants import INSTRUCTIONS_DIR
from tree import custom_tree

# ---------------------------------------------------------------------------
# Remote directory helper
# ---------------------------------------------------------------------------

def custom_remote_tree(root_path: str, ssh_cmd: str,
                       prefix: str = "", level: int = 1,
                       max_level: int = 999, blacklist: list[str] | None = None):
    """
    Build a text tree of *root_path* on a remote host accessed via *ssh_cmd*.
    """
    from setup.remote_utils import get_remote_tree, parse_remote_tree, filter_tree_dict
    lines = get_remote_tree(root_path, ssh_cmd)
    tree_dict = parse_remote_tree(lines, root_path)
    if blacklist:
        tree_dict = filter_tree_dict(tree_dict, root_path, blacklist, root_path)

    def recurse(d, pref):
        out = []
        keys = sorted(d.keys())
        for idx, name in enumerate(keys):
            connector = "├── " if idx < len(keys)-1 else "└── "
            out.append(pref + connector + name)
            if d[name]:
                ext = "│   " if idx < len(keys)-1 else "    "
                out.extend(recurse(d[name], pref + ext))
        return out

    return recurse(tree_dict, prefix)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_local(fname: str) -> str:
    fp = os.path.join(INSTRUCTIONS_DIR, fname)
    try:
        with open(fp, "r") as f:
            return f.read()
    except Exception:
        return ""

def _write_temp(txt: str) -> str:
    tf = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    tf.write(txt)
    tf.close()
    return tf.name

# ---------------------------------------------------------------------------
# STEP 1  –  build “setup” text block
# ---------------------------------------------------------------------------

def step1(config: dict) -> str:
    """
    Return one big string consisting of
        background.txt
        + directory tree(s)
        + rules.txt
        + current_goal.txt
        + optional extra project-output files
    No editor window is opened here; the caller decides what to do with the
    resulting text.
    """
    background   = _read_local("background.txt")
    rules        = _read_local("rules.txt")
    current_goal = _read_local("current_goal.txt")

    # ---------------- directory-tree(s) -----------------------
    if config.get("has_single_root"):
        root = config["project_root"]
        if config.get("system_type") == "remote":
            ssh = config.get("ssh_command", "")
            bl  = config.get("blacklist", {}).get(root, [])
            lines = [root] + custom_remote_tree(root, ssh, "", 1, 999, bl)
        else:
            bl  = config.get("blacklist", {}).get(root, [])
            lines = [root] + custom_tree(root, "", 1, 999, bl, root)
        tree_text = "\n".join(lines)
    else:
        seg_chunks = []
        for seg in config.get("directories", []):
            seg_root = seg["directory"]
            seg_chunks.append(f"Segment: {seg['name']} => {seg_root}")
            if seg.get("is_remote"):
                ssh = config.get("ssh_command", "")
                bl  = config.get("blacklist", {}).get(seg_root, [])
                seg_lines = [seg_root] + custom_remote_tree(seg_root, ssh, "", 1, 999, bl)
            else:
                bl  = config.get("blacklist", {}).get(seg_root, [])
                seg_lines = [seg_root] + custom_tree(seg_root, "", 1, 999, bl, seg_root)
            seg_chunks.extend(seg_lines)
            seg_chunks.append("")
        tree_text = "\n".join(seg_chunks)

    # ---------------- assemble core section -------------------
    parts = []
    if background.strip():   parts.append(background.rstrip())
    if tree_text.strip():    parts.append(tree_text.rstrip())
    if rules.strip():        parts.append(rules.rstrip())
    if current_goal.strip(): parts.append(current_goal.rstrip())
    txt = "\n\n".join(parts) + "\n\n"

    # ---------------- append extra files ----------------------
    def _cat_local(fp):
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                return f.read().rstrip()
        except Exception:
            return ""
    def _cat_remote(ssh_cmd, fp):
        try:
            proc = subprocess.run(ssh_cmd.split()+["cat", fp], capture_output=True, text=True)
            return proc.stdout.rstrip() if proc.returncode == 0 else ""
        except Exception:
            return ""

    extras = []
    if config.get("has_single_root"):
        for fp in config.get("project_output_files", []):
            extras.append(
                _cat_remote(config.get("ssh_command",""), fp)
                if config.get("system_type") == "remote"
                else _cat_local(fp)
            )
    else:
        for seg in config.get("directories", []):
            for fp in seg.get("output_files", []):
                extras.append(
                    _cat_remote(config.get("ssh_command",""), fp)
                    if seg.get("is_remote")
                    else _cat_local(fp)
                )
    if extras:
        txt += "Project Output Files:\n\n" + "\n\n".join([e for e in extras if e]) + "\n"

    return txt

# ---------------------------------------------------------------------------
# STEP 2  –  collect file-content per segment
# ---------------------------------------------------------------------------

def step2_all_segments(config: dict) -> str:
    """
    Spawn a file-selection GUI for each segment and return a single string
    containing the concatenated content of all user-selected files
    (triple-newline separated). No editor windows are opened here.
    """
    from gui import gui_selection
    from setup.content_setup import is_rel_path_blacklisted

    blobs = []
    project_root = os.path.abspath(config.get("project_root", os.getcwd()))
    color_cycle = ["light blue", "lavender", "light green", "light yellow", "light coral"]

    for idx, seg in enumerate(config.get("directories", [])):
        print(f"Starting file selection for segment '{seg['name']}'")
        selected = gui_selection(
            f"Select Files for {seg['name']}",
            color_cycle[idx % len(color_cycle)],
            seg["directory"],
            seg["name"],
            seg.get("is_remote", False),
            config.get("ssh_command","") if seg.get("is_remote") else "",
            config.get("blacklist", {}),
            project_root
        )
        seg["output_files"] = selected

        seg_texts = []
        for fp in selected:
            if seg.get("is_remote"):
                try:
                    proc = subprocess.run(config.get("ssh_command","").split()+["cat", fp],
                                          capture_output=True, text=True)
                    if proc.returncode == 0:
                        seg_texts.append(proc.stdout.rstrip())
                except Exception:
                    pass
            else:
                if os.path.exists(fp):
                    try:
                        with open(fp, "r", encoding="utf-8", errors="replace") as f:
                            seg_texts.append(f.read().rstrip())
                    except Exception:
                        pass
        if seg_texts:
            blobs.append("\n\n".join(seg_texts))

    return "\n\n\n".join(blobs)
