# annotate_files.py
"""
annotate_files.py
-----------------
Add a first-line header comment that records the *relative* path of each file
(from the project-root the user supplies) in a single, unambiguous form:

    #  tools/file_tools/misc/my_tool.py
    // tools/frontend/app/layout.tsx
    /* tools/static/css/main.css */

The header is inserted **after** any shebang (`#!`) line and skipped when the
correct annotation already exists (those files are greyed out in the picker).
Only files ticked in the Tk window are modified.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import tkinter as tk

# --------------------------------------------------------------------------- #
#  Load config & blacklist helpers
# --------------------------------------------------------------------------- #

try:
    from setup.constants import CONFIG_FILE  # type: ignore
except ImportError:
    CONFIG_FILE = "gpt_helper_config.json"

if not os.path.exists(CONFIG_FILE):
    print("[annotate_files]  No configuration found.  Run "
          "`python main.py --setup` first, then re-run this tool.")
    sys.exit(1)

try:
    with open(CONFIG_FILE, "r") as jf:
        CFG = json.load(jf)
except Exception as exc:
    print(f"[annotate_files]  Error reading {CONFIG_FILE}: {exc}")
    sys.exit(1)

BLACKLIST: Dict[str, List[str]] = CFG.get("blacklist", {})

# --------------------------------------------------------------------------- #
#  Blacklist helpers (portable fallback if setup.* import fails)
# --------------------------------------------------------------------------- #
try:
    from setup.content_setup import is_rel_path_blacklisted  # type: ignore
except Exception:  # pragma: no cover – only used outside the full project
    def is_rel_path_blacklisted(rel_path: str, bl: List[str]) -> bool:
        rel_path = rel_path.strip("/\\")
        for b in bl:
            b = b.strip("/\\")
            if (rel_path == b or rel_path.startswith(b + os.sep)
                    or rel_path.startswith(b + "/")):
                return True
        return False


def is_abs_path_blacklisted(abs_path: str) -> bool:
    abs_path = os.path.abspath(abs_path)
    for root, rels in BLACKLIST.items():
        root = os.path.abspath(root)
        if abs_path == root or abs_path.startswith(root + os.sep):
            rel = os.path.relpath(abs_path, root).strip(os.sep)
            if not rel or is_rel_path_blacklisted(rel, rels):
                return True
    return False

# --------------------------------------------------------------------------- #
#  Comment-syntax helpers
# --------------------------------------------------------------------------- #
_COMMENT_PREFIX: Dict[str, str] = {
    ".py": "#", ".yml": "#", ".yaml": "#", ".sh": "#",
    ".rb": "#", ".ps1": "#", ".psm1": "#", ".tf": "#",
    ".bashrc": "#", ".zshrc": "#",
    "Dockerfile": "#",

    ".js": "//", ".jsx": "//", ".ts": "//", ".tsx": "//",
    ".c": "//", ".cpp": "//", ".h": "//", ".hpp": "//",
    ".cs": "//", ".java": "//", ".kt": "//", ".kts": "//",
    ".go": "//", ".swift": "//", ".php": "//",

    ".sql": "--",

    ".css": "/*", ".scss": "/*",
    ".html": "<!--", ".htm": "<!--", ".xml": "<!--",
    ".md": "<!--", ".markdown": "<!--",
    ".json": "//",  # technically disallowed, but pragmatic for context files
}


def comment_symbols(fname: str) -> Tuple[str, str]:
    """
    Return (prefix, suffix) to wrap a single-line comment.  The suffix is
    empty for `#`, `//`, `--`; it is `' */'` for C-style and `' -->'`
    for HTML/XML comments.
    """
    base = os.path.basename(fname)
    ext = os.path.splitext(base)[1].lower()

    if base == "Dockerfile":
        return "#", ""

    pref = _COMMENT_PREFIX.get(base) or _COMMENT_PREFIX.get(ext)
    if pref in ("#",
                "//",
                "--"):
        return pref, ""
    if pref == "/*":
        return "/*", " */"
    if pref == "<!--":
        return "<!--", " -->"
    # Fallback: safest is shell style so the file stays runnable
    return "#", ""


# --------------------------------------------------------------------------- #
#  Header-detection helpers
# --------------------------------------------------------------------------- #
_RE_CACHE: Dict[str, re.Pattern[str]] = {}


def _header_regex(text: str) -> re.Pattern[str]:
    """
    Compile (and cache) a regex that matches the correct annotation for *text*
    regardless of leading/trailing whitespace.
    """
    pat = rf"^\s*(#|//|--|/\*|<!--)\s*{re.escape(text)}\s*(\*/|-->)?\s*$"
    if pat not in _RE_CACHE:
        _RE_CACHE[pat] = re.compile(pat)
    return _RE_CACHE[pat]


def file_has_header(lines: List[str], header_text: str) -> bool:
    """
    Return True when *lines* already contain the correct annotation on the
    first logical line (after any shebang).
    """
    idx = 1 if lines and lines[0].startswith("#!") else 0
    if idx >= len(lines):
        return False
    return bool(_header_regex(header_text).match(lines[idx]))


# --------------------------------------------------------------------------- #
#  Remote helpers
# --------------------------------------------------------------------------- #
def remote_find_all(ssh: str, root: str) -> List[str]:
    """
    Return a list of *files* (not directories) on the remote host.  We use
    `find -type f` so no extra stat calls are needed later.
    """
    try:
        proc = subprocess.run(
            ssh.split() + ["find", root, "-type", "f", "-print"],
            capture_output=True, text=True, timeout=60
        )
        return proc.stdout.splitlines() if proc.returncode == 0 else []
    except Exception:
        return []


def remote_cat(ssh: str, fp: str, num_lines: int | None = None) -> str | None:
    """
    Read the entire remote file (or the first *num_lines* if given).
    """
    try:
        if num_lines is None:
            cmd = ssh.split() + ["cat", fp]
        else:
            # head -n handles CR/LF and is cheaper than full cat + split
            cmd = ssh.split() + ["head", "-n", str(num_lines), fp]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return proc.stdout if proc.returncode == 0 else None
    except Exception:
        return None


def remote_write(ssh: str, fp: str, data: str) -> bool:
    """
    Atomically replace *fp* on the remote host with *data* using a temp file.
    """
    tmp = f"{fp}.__tmp_header"
    try:
        # Create tmp
        if subprocess.run(
            ssh.split() + ["bash", "-c", f"cat > {tmp}"],
            input=data, text=True
        ).returncode != 0:
            return False
        # Move into place
        return subprocess.run(
            ssh.split() + ["mv", tmp, fp]
        ).returncode == 0
    except Exception:
        return False


# --------------------------------------------------------------------------- #
#  Wizard – ask user for project root
# --------------------------------------------------------------------------- #
def ask_root() -> Dict[str, str] | None:
    """
    Ask for the project-root directory (local or remote).  
    Prefills the entry with:
        • CFG["project_root"]  if present
        • else  common prefix of CFG["directories"][].directory
        • else  empty
    """
    # ----- figure out the best default root ---------------------------------
    if CFG.get("project_root"):
        default_root = CFG["project_root"]
    else:
        dirs = [d.get("directory", "") for d in CFG.get("directories", [])]
        default_root = os.path.commonpath(dirs) if dirs else ""

    result: Dict[str, str] | None = None
    w = tk.Tk()
    w.title("Annotation – Select Project Root")

    # row 0 – directory path --------------------------------------------------
    tk.Label(w, text="Project root directory:")\
        .grid(row=0, column=0, padx=5, pady=5, sticky="w")
    ent_root = tk.Entry(w, width=60)
    ent_root.grid(row=0, column=1, padx=5, pady=5)
    if default_root:
        ent_root.insert(0, default_root)

    # row 1 – local / remote toggle ------------------------------------------
    remote_flag = tk.IntVar(value=0)
    tk.Radiobutton(w, text="Local",  variable=remote_flag, value=0)\
        .grid(row=1, column=0, sticky="w", padx=5)
    tk.Radiobutton(w, text="Remote", variable=remote_flag, value=1)\
        .grid(row=1, column=1, sticky="w", padx=5)

    # row 2 – SSH entry (only when remote) ------------------------------------
    lbl_ssh = tk.Label(w, text="SSH command (e.g. ssh my-vps):")
    ent_ssh = tk.Entry(w, width=60)

    def _toggle_remote(*_):
        if remote_flag.get():
            lbl_ssh.grid(row=2, column=0, padx=5, pady=5, sticky="w")
            ent_ssh.grid(row=2, column=1, padx=5, pady=5)
            if not ent_ssh.get().strip() and CFG.get("ssh_command"):
                ent_ssh.insert(0, CFG["ssh_command"])
        else:
            lbl_ssh.grid_remove()
            ent_ssh.grid_remove()

    remote_flag.trace_add("write", _toggle_remote)
    _toggle_remote()

    # status label + buttons --------------------------------------------------
    lbl_status = tk.Label(w, text="", fg="blue")
    lbl_status.grid(row=3, column=0, columnspan=2)

    btns = tk.Frame(w); btns.grid(row=4, column=0, columnspan=2, pady=10)

    def _verify():
        path = ent_root.get().strip()
        if not path:
            lbl_status.config(text="Path required.", fg="red"); return

        if remote_flag.get() == 0:            # local
            ok = os.path.isdir(path)
        else:                                 # remote
            ssh_cmd = ent_ssh.get().strip()
            if not ssh_cmd:
                lbl_status.config(text="SSH command required.", fg="red")
                return
            ok = subprocess.run(
                ssh_cmd.split() + ["test", "-d", path]).returncode == 0

        lbl_status.config(
            text="Directory verified." if ok else "Directory not found.",
            fg="green" if ok else "red")
        btn_go.config(state="normal" if ok else "disabled")

    tk.Button(btns, text="Verify",  width=10, command=_verify)\
        .pack(side="left", padx=5)
    tk.Button(btns, text="Cancel",  width=10, command=w.destroy)\
        .pack(side="left", padx=5)

    def _proceed():
        nonlocal result
        result = {
            "root": os.path.abspath(ent_root.get().strip()),
            "remote": bool(remote_flag.get()),
            "ssh": ent_ssh.get().strip(),
        }
        w.destroy()

    btn_go = tk.Button(btns, text="Proceed", width=10,
                       command=_proceed, state="disabled")
    btn_go.pack(side="left", padx=5)

    w.mainloop()
    return result



# --------------------------------------------------------------------------- #
#  Build file list (respecting blacklist) – local & remote
# --------------------------------------------------------------------------- #
def build_local_items(base: str) -> List[Dict]:
    items: List[Dict[str, object]] = []
    base_depth = Path(base).as_posix().count('/')
    for root, dirs, files in os.walk(base, topdown=True):
        dirs[:] = [d for d in dirs
                   if not is_abs_path_blacklisted(os.path.join(root, d))]
        depth = Path(root).as_posix().count('/') - base_depth
        for f in sorted(files):
            fp = os.path.join(root, f)
            if not is_abs_path_blacklisted(fp):
                items.append({"path": fp, "indent": depth})
    return items


def build_remote_items(ssh: str, base: str) -> List[Dict]:
    items: List[Dict[str, object]] = []
    for full in remote_find_all(ssh, base):
        if is_abs_path_blacklisted(full):
            continue
        depth = Path(full).as_posix().count('/') - Path(base).as_posix().count('/')
        items.append({"path": full, "indent": depth})
    return items


# --------------------------------------------------------------------------- #
#  Tk file-selection GUI (auto-sizes to content)
# --------------------------------------------------------------------------- #
class SelectionGUI:
    def __init__(self,
                 master: tk.Tk,
                 items,
                 base_dir: str,
                 remote: bool,
                 ssh: str):
        self.master = master
        self.selected: List[str] = []
        self.vars: Dict[str, tk.BooleanVar] = {}

        self.base_dir = Path(base_dir)
        self.root_name = self.base_dir.name
        self.remote = remote
        self.ssh = ssh

        master.title("Select files to annotate")

        # ------------ scrollable canvas scaffold ---------------------------
        self.canvas = tk.Canvas(master, borderwidth=0, highlightthickness=0)
        vscroll = tk.Scrollbar(master, orient="vertical",
                               command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vscroll.set)

        vscroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=frame, anchor="nw")

        # Cross-platform mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>",  self._on_mousewheel)
        self.canvas.bind_all("<Button-5>",  self._on_mousewheel)

        # ------------ populate the list ------------------------------------
        for itm in items:
            rel = Path(itm["path"]).relative_to(self.base_dir).as_posix()
            indent = "    " * itm["indent"]
            disp   = f"{indent}{rel}"
            header = f"{self.root_name}/{rel}"

            # Peek first few lines
            if remote:
                peek = (remote_cat(ssh, itm["path"], 3) or "").splitlines()
            else:
                try:
                    with open(itm["path"], "r", encoding="utf-8",
                              errors="replace") as f:
                        peek = [next(f).rstrip("\n") for _ in range(3)]
                except Exception:
                    peek = []

            already = file_has_header(peek, header)

            if already:
                tk.Checkbutton(frame, text=disp, state=tk.DISABLED,
                               fg="grey", anchor="w")\
                    .pack(anchor="w", padx=5)
            else:
                var = tk.BooleanVar()
                self.vars[itm["path"]] = var
                cb = tk.Checkbutton(frame, text=disp, variable=var,
                                    anchor="w", highlightthickness=0, bd=0)
                cb.bind("<Double-1>", lambda _e, v=var: v.set(not v.get()))
                cb.pack(anchor="w", padx=5)

        # ------------ buttons ----------------------------------------------
        btns = tk.Frame(master)
        btns.pack(pady=6)
        tk.Button(btns, text="Finish",  width=10,
                  command=self.finish).pack(side="left", padx=4)
        tk.Button(btns, text="Cancel",  width=10,
                  command=self.cancel).pack(side="left", padx=4)

        # ------------ final sizing pass ------------------------------------
        master.update_idletasks()            # let Tk compute real sizes

        scr_w, scr_h = master.winfo_screenwidth(), master.winfo_screenheight()

        list_w  = frame.winfo_reqwidth()                 # file list
        btn_w   = btns.winfo_reqwidth()                  # Finish / Cancel
        sb_w    = vscroll.winfo_reqwidth()               # scrollbar

        content_w = max(list_w + sb_w, btn_w) + 300       # + padding
        content_h = frame.winfo_reqheight() + btns.winfo_reqheight() + 24

        win_w = min(content_w, scr_w - 40)
        win_h = min(content_h, scr_h - 80)

        x = (scr_w - win_w) // 2
        y = (scr_h - win_h) // 2
        master.geometry(f"{win_w}x{win_h}+{x}+{y}")

    # ------------------------------------------------------------------- #
    #  helpers
    # ------------------------------------------------------------------- #
    def _on_mousewheel(self, event):
        if event.num == 4:                # X11 up
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:              # X11 down
            self.canvas.yview_scroll(1, "units")
        else:                             # Win / macOS
            self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    def finish(self):
        self.selected = [p for p, v in self.vars.items() if v.get()]
        self.master.destroy()

    def cancel(self):
        self.master.destroy()
        sys.exit(0)




# --------------------------------------------------------------------------- #
#  Header construction & annotation helpers
# --------------------------------------------------------------------------- #
def build_header(base: Path, file_path: Path) -> str:
    return f"{base.name}/{file_path.relative_to(base).as_posix()}"


def annotate_local(fp: Path, base: Path) -> bool:
    hdr = build_header(base, fp)
    pref, suf = comment_symbols(fp.name)
    try:
        lines = fp.read_text(encoding="utf-8", errors="replace")\
                  .splitlines(keepends=True)
    except Exception as e:
        print(f"  ✗ {hdr} (read error: {e})")
        return False

    if file_has_header([ln.rstrip('\n') for ln in lines[:3]], hdr):
        return False

    idx = 1 if lines and lines[0].startswith("#!") else 0
    lines.insert(idx, f"{pref} {hdr}{suf}\n")

    try:
        fp.write_text("".join(lines), encoding="utf-8")
        print(f"  ✔ {hdr}")
        return True
    except Exception as e:
        print(f"  ✗ {hdr} (write error: {e})")
        return False


def annotate_remote(fp: str, base: str, ssh: str) -> bool:
    hdr = build_header(Path(base), Path(fp))
    txt = remote_cat(ssh, fp)
    if txt is None:
        print(f"  ✗ {hdr} (read failure)")
        return False

    lines = txt.splitlines(keepends=True)
    if file_has_header([ln.rstrip('\n') for ln in lines[:3]], hdr):
        return False

    pref, suf = comment_symbols(fp)
    idx = 1 if lines and lines[0].startswith("#!") else 0
    lines.insert(idx, f"{pref} {hdr}{suf}\n")

    if remote_write(ssh, fp, "".join(lines)):
        print(f"  ✔ {hdr}")
        return True

    print(f"  ✗ {hdr} (write failure)")
    return False


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #
def main() -> None:
    info = ask_root()
    if not info:
        return

    base = info["root"]
    remote = info["remote"]
    ssh = info["ssh"]

    print("Building file list …")
    items = build_remote_items(ssh, base) if remote else build_local_items(base)

    root = tk.Tk()
    gui = SelectionGUI(root, items, base, remote, ssh)
    root.mainloop()

    print("\nAnnotating …")
    changed = 0
    if remote:
        for p in gui.selected:
            if annotate_remote(p, base, ssh):
                changed += 1
    else:
        for p in gui.selected:
            if annotate_local(Path(p), Path(base)):
                changed += 1

    print(f"Done – {changed} file(s) updated.")


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
