# gpt_helper/dev/gui/annotation_manager.py
"""
Annotation Manager - GUI integration for file annotation functionality
"""
import os
import re
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set

# Import from parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from annotate_files import (
        comment_symbols, file_has_header, build_header,
        remote_cat, remote_write, _header_regex
    )
except ImportError:
    # Fallback imports if annotate_files is not in expected location
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from annotate_files import (
        comment_symbols, file_has_header, build_header,
        remote_cat, remote_write, _header_regex
    )

from setup.content_setup import is_rel_path_blacklisted
from setup.constants import CONFIG_FILE


class AnnotationManager:
    """Manages file annotation status and operations"""
    
    def __init__(self, config: dict):
        self.config = config
        self.project_root = Path(config.get("project_root", os.getcwd()))
        self.blacklist = config.get("blacklist", {})
        self.ssh_command = config.get("ssh_command", "")
        
        # Cache for performance
        self.file_status_cache = {}
        self.last_scan_time = None
        self._temp_scan_results = {}  # Temporary storage for scan results during annotation
        
    def scan_directory(self, directory: str, is_remote: bool = False) -> Dict[str, Dict]:
        """
        Scan directory and return file annotation status
        Returns: {filepath: {"annotated": bool, "correct": bool, "type": str}}
        """
        results = {}
        base_path = Path(directory)
        
        if is_remote:
            files = self._scan_remote_directory(directory)
        else:
            files = self._scan_local_directory(directory)
        
        for filepath in files:
            # Check blacklist
            rel_path = os.path.relpath(filepath, directory)
            if is_rel_path_blacklisted(rel_path, self.blacklist.get(directory, [])):
                continue
            
            # Check annotation status
            status = self._check_file_annotation(filepath, base_path, is_remote)
            results[filepath] = status
        
        return results
    
    def _scan_local_directory(self, directory: str) -> List[str]:
        """Recursively scan local directory for files"""
        files = []
        for root, dirs, filenames in os.walk(directory):
            # Filter out blacklisted directories
            dirs[:] = [d for d in dirs if not is_rel_path_blacklisted(
                os.path.relpath(os.path.join(root, d), directory),
                self.blacklist.get(directory, [])
            )]
            
            for filename in filenames:
                filepath = os.path.join(root, filename)
                files.append(filepath)
        
        return files
    
    def _scan_remote_directory(self, directory: str) -> List[str]:
        """Scan remote directory for files"""
        try:
            cmd = f"{self.ssh_command} find {directory} -type f -print"
            proc = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=60)
            if proc.returncode == 0:
                return proc.stdout.strip().split('\n') if proc.stdout.strip() else []
        except:
            pass
        return []
    
    def _check_file_annotation(self, filepath: str, base_path: Path, is_remote: bool) -> Dict:
        """Check if file has correct annotation"""
        # Get expected header - try multiple formats
        rel_path = Path(filepath).relative_to(base_path).as_posix()
        
        # Try different header formats
        possible_headers = [
            # Format 1: project_name/path/to/file.py (most common)
            f"{base_path.name}/{rel_path}",
            # Format 2: full relative path from a parent directory
            f"gpt_helper/dev/{rel_path}",
            # Format 3: just the relative path
            rel_path,
        ]
        
        # Read first few lines
        first_lines = []
        if is_remote:
            content = remote_cat(self.ssh_command, filepath, 4)
            first_lines = content.split('\n') if content else []
        else:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    first_lines = [f.readline().rstrip('\n') for _ in range(4)]
            except:
                first_lines = []
        
        # Check if any header format matches
        has_header = False
        actual_header = ""
        expected_header = possible_headers[0]  # Default expected
        
        # Check each line for a header
        for line in first_lines[:3]:  # Check first 3 lines
            # Skip shebang
            if line.startswith('#!'):
                continue
            
            # Extract potential header from comment
            header_match = None
            if line.startswith('# '):
                header_match = line[2:].strip()
            elif line.startswith('// '):
                header_match = line[3:].strip()
            elif line.startswith('/* ') and line.endswith(' */'):
                header_match = line[3:-3].strip()
            elif line.startswith('<!-- ') and line.endswith(' -->'):
                header_match = line[5:-4].strip()
            
            if header_match:
                # Check if it matches any expected format
                for possible in possible_headers:
                    if header_match == possible or header_match.endswith('/' + possible):
                        has_header = True
                        actual_header = header_match
                        expected_header = header_match  # Use the working format
                        break
                
                # Also check if it's a valid path-like annotation
                if not has_header and '/' in header_match and header_match.endswith(os.path.basename(filepath)):
                    has_header = True
                    actual_header = header_match
                    expected_header = header_match
                
                break
        
        # Determine file type for icon
        ext = os.path.splitext(filepath)[1].lower()
        file_type = self._get_file_type(ext)
        
        return {
            "annotated": has_header,
            "correct": has_header,
            "type": file_type,
            "expected_header": expected_header,
            "actual_header": actual_header,
            "first_lines": first_lines[:4]  # Store first 4 lines for preview
        }
    
    def _get_file_type(self, ext: str) -> str:
        """Get file type for icon display"""
        type_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.scss': 'css',
            '.json': 'json',
            '.xml': 'xml',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.md': 'markdown',
            '.txt': 'text',
            '.sh': 'shell',
            '.bash': 'shell',
            '.zsh': 'shell',
            '.sql': 'sql',
            'Dockerfile': 'docker',
            '.env': 'env'
        }
        
        return type_map.get(ext, 'file')
    
    def annotate_files(self, filepaths: List[str], is_remote: bool = False, 
                      progress_callback=None, scan_results=None) -> Dict[str, bool]:
        """
        Annotate multiple files
        Returns: {filepath: success}
        """
        results = {}
        total = len(filepaths)
        
        # Store scan results for use in annotate_single_file
        self._temp_scan_results = scan_results or {}
        
        for i, filepath in enumerate(filepaths):
            if progress_callback:
                progress_callback(i, total, f"Annotating {os.path.basename(filepath)}")
            
            success = self.annotate_single_file(filepath, is_remote)
            results[filepath] = success
        
        if progress_callback:
            progress_callback(total, total, "Annotation complete")
        
        # Clear temp results
        self._temp_scan_results = {}
        
        return results
    
    def annotate_single_file(self, filepath: str, is_remote: bool = False) -> bool:
        """Annotate a single file"""
        # Find the base path for this file
        base_path = None
        for directory in self.config.get("directories", []):
            if filepath.startswith(directory["directory"]):
                base_path = Path(directory["directory"])
                break
        
        if not base_path:
            base_path = self.project_root
        
        # Get the expected header from scan results if available
        info = getattr(self, '_temp_scan_results', {}).get(filepath, {})
        header = info.get("expected_header")
        
        if not header:
            # Fallback to build_header
            header = build_header(base_path, Path(filepath))
        
        prefix, suffix = comment_symbols(os.path.basename(filepath))
        header_line = f"{prefix} {header}{suffix}\n"
        
        if is_remote:
            return self._annotate_remote_file(filepath, header_line)
        else:
            return self._annotate_local_file(filepath, header_line)
    
    def _annotate_local_file(self, filepath: str, header_line: str) -> bool:
        """Add annotation to local file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            # Skip if already has correct header
            if lines and file_has_header([l.strip() for l in lines[:3]], 
                                        header_line.strip().strip('# ')):
                return True
            
            # Insert after shebang if present
            insert_idx = 1 if lines and lines[0].startswith('#!') else 0
            lines.insert(insert_idx, header_line)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
        except Exception as e:
            print(f"Error annotating {filepath}: {e}")
            return False
    
    def _annotate_remote_file(self, filepath: str, header_line: str) -> bool:
        """Add annotation to remote file"""
        try:
            # Read file
            content = remote_cat(self.ssh_command, filepath)
            if content is None:
                return False
            
            lines = content.splitlines(keepends=True)
            
            # Skip if already has correct header
            if lines and file_has_header([l.strip() for l in lines[:3]], 
                                        header_line.strip().strip('# ')):
                return True
            
            # Insert after shebang if present
            insert_idx = 1 if lines and lines[0].startswith('#!') else 0
            lines.insert(insert_idx, header_line)
            
            # Write back
            return remote_write(self.ssh_command, filepath, ''.join(lines))
        except Exception as e:
            print(f"Error annotating remote {filepath}: {e}")
            return False
    
    def get_statistics(self, directories: List[Dict]) -> Dict:
        """Get annotation statistics for given directories"""
        total_files = 0
        annotated_files = 0
        missing_files = 0
        
        for directory in directories:
            status = self.scan_directory(
                directory["directory"], 
                directory.get("is_remote", False)
            )
            
            for file_info in status.values():
                total_files += 1
                if file_info["annotated"]:
                    annotated_files += 1
                else:
                    missing_files += 1
        
        return {
            "total": total_files,
            "annotated": annotated_files,
            "missing": missing_files,
            "percentage": (annotated_files / total_files * 100) if total_files > 0 else 0
        }


class AnnotationManagerTab(ttk.Frame):
    """GUI tab for annotation management"""
    
    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.config = config
        self.manager = AnnotationManager(config)
        self.selected_files = set()
        self.current_scan_results = {}
        
        # Initialize UI variables
        self.expected_header_var = None
        self.current_header_var = None
        self.preview_text = None
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header section
        self._create_header_section(main_frame)
        
        # Statistics section
        self._create_stats_section(main_frame)
        
        # File tree section
        self._create_file_tree_section(main_frame)
        
        # Action buttons section
        self._create_action_section(main_frame)
        
        # Progress section
        self._create_progress_section(main_frame)
    
    def _create_header_section(self, parent):
        """Create header with title and scan button"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="File Annotation Manager", 
                               font=('TkDefaultFont', 12, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        scan_btn = ttk.Button(header_frame, text="🔄 Scan Project", 
                             command=self.scan_project)
        scan_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.last_scan_label = ttk.Label(header_frame, text="", 
                                        font=('TkDefaultFont', 9))
        self.last_scan_label.pack(side=tk.RIGHT, padx=(10, 0))
    
    def _create_stats_section(self, parent):
        """Create statistics display section"""
        stats_frame = ttk.LabelFrame(parent, text="Annotation Statistics", padding="10")
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        # Create stat labels
        self.stats_labels = {}
        stat_items = [
            ("total", "Total Files:", "blue"),
            ("annotated", "Annotated:", "green"),
            ("missing", "Missing:", "orange"),
            ("percentage", "Coverage:", "purple")
        ]
        
        for i, (key, label, color) in enumerate(stat_items):
            frame = ttk.Frame(stats_frame)
            frame.grid(row=0, column=i, padx=10)
            
            ttk.Label(frame, text=label).pack()
            value_label = ttk.Label(frame, text="—", font=('TkDefaultFont', 14, 'bold'))
            value_label.pack()
            self.stats_labels[key] = value_label
        
        # Progress bar for coverage
        self.coverage_progress = ttk.Progressbar(stats_frame, mode='determinate', 
                                               length=300)
        self.coverage_progress.grid(row=1, column=0, columnspan=4, pady=(10, 0), 
                                   sticky="ew")
    
    def _create_file_tree_section(self, parent):
        """Create file tree display section"""
        # Main container with paned window
        paned = ttk.PanedWindow(parent, orient="horizontal")
        paned.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        parent.grid_rowconfigure(2, weight=1)
        
        # Left side - tree view
        tree_frame = ttk.LabelFrame(paned, text="Files Missing Annotations", 
                                   padding="10")
        
        # Toolbar
        toolbar = ttk.Frame(tree_frame)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Button(toolbar, text="Select All", 
                  command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Select None", 
                  command=self.select_none).pack(side=tk.LEFT, padx=(0, 5))
        
        # Filter options
        ttk.Label(toolbar, text="Filter:").pack(side=tk.LEFT, padx=(20, 5))
        self.filter_var = tk.StringVar(value="missing")
        filter_combo = ttk.Combobox(toolbar, textvariable=self.filter_var,
                                   values=["all", "missing", "annotated"],
                                   state="readonly", width=10)
        filter_combo.pack(side=tk.LEFT)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_tree())
        
        # Tree view with scrollbar
        tree_container = ttk.Frame(tree_frame)
        tree_container.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(1, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        self.file_tree = ttk.Treeview(tree_container, columns=("status", "type", "header"),
                                     show="tree headings", selectmode="extended")
        
        # Configure columns
        self.file_tree.heading("#0", text="File")
        self.file_tree.heading("status", text="Status")
        self.file_tree.heading("type", text="Type")
        self.file_tree.heading("header", text="Expected Header")
        
        self.file_tree.column("#0", width=250)
        self.file_tree.column("status", width=80)
        self.file_tree.column("type", width=60)
        self.file_tree.column("header", width=300)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_container, orient="vertical", 
                           command=self.file_tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", 
                           command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Bind selection event
        self.file_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # Selection info
        self.selection_label = ttk.Label(tree_frame, text="0 files selected")
        self.selection_label.grid(row=2, column=0, sticky="w", pady=(5, 0))
        
        # Add tree frame to paned window
        paned.add(tree_frame, weight=2)
        
        # Right side - file preview
        preview_frame = ttk.LabelFrame(paned, text="File Preview", padding="10")
        
        # Header info section
        header_info_frame = ttk.Frame(preview_frame)
        header_info_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(header_info_frame, text="Expected Header:", 
                 font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, sticky="w")
        self.expected_header_var = tk.StringVar()
        self.expected_header_label = ttk.Label(header_info_frame, 
                                             textvariable=self.expected_header_var,
                                             font=('Consolas', 9))
        self.expected_header_label.grid(row=0, column=1, sticky="w", padx=(5, 0))
        
        ttk.Label(header_info_frame, text="Current Header:", 
                 font=('TkDefaultFont', 9, 'bold')).grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.current_header_var = tk.StringVar()
        self.current_header_label = ttk.Label(header_info_frame, 
                                            textvariable=self.current_header_var,
                                            font=('Consolas', 9))
        self.current_header_label.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=(5, 0))
        
        # Edit header button
        ttk.Button(header_info_frame, text="Edit Format", 
                  command=self.edit_header_format).grid(row=0, column=2, padx=(10, 0))
        
        # Code preview
        ttk.Label(preview_frame, text="First 4 Lines:", 
                 font=('TkDefaultFont', 9, 'bold')).pack(anchor="w", pady=(5, 5))
        
        # Create text widget with syntax highlighting
        self.preview_text = tk.Text(preview_frame, height=6, width=60,
                                   bg="#1e1e1e", fg="#d4d4d4",
                                   font=('Consolas', 10),
                                   wrap="none")
        self.preview_text.pack(fill="both", expand=True)
        
        # Configure syntax highlighting tags
        self._setup_syntax_tags()
        
        # Make preview read-only
        self.preview_text.config(state="disabled")
        
        # Add preview frame to paned window
        paned.add(preview_frame, weight=1)
    
    def _create_action_section(self, parent):
        """Create action buttons section"""
        action_frame = ttk.Frame(parent)
        action_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        
        # Primary actions
        primary_frame = ttk.Frame(action_frame)
        primary_frame.pack(side=tk.LEFT)
        
        self.annotate_selected_btn = ttk.Button(
            primary_frame, text="✏️ Annotate Selected", 
            command=self.annotate_selected, state="disabled"
        )
        self.annotate_selected_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.annotate_all_btn = ttk.Button(
            primary_frame, text="📝 Annotate All Missing", 
            command=self.annotate_all_missing
        )
        self.annotate_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Secondary actions
        secondary_frame = ttk.Frame(action_frame)
        secondary_frame.pack(side=tk.RIGHT)
        
        ttk.Button(secondary_frame, text="🔍 Verify Annotations", 
                  command=self.verify_annotations).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(secondary_frame, text="👁️ Preview", 
                  command=self.preview_annotation).pack(side=tk.LEFT)
    
    def _create_progress_section(self, parent):
        """Create progress display section"""
        self.progress_frame = ttk.Frame(parent)
        self.progress_frame.grid(row=4, column=0, sticky="ew")
        self.progress_frame.grid_remove()  # Hidden by default
        
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate',
                                          length=400)
        self.progress_bar.pack(pady=(5, 0))
    
    def _setup_syntax_tags(self):
        """Setup syntax highlighting tags for code preview"""
        # Comment style
        self.preview_text.tag_configure("comment", foreground="#6a9955")
        # String style
        self.preview_text.tag_configure("string", foreground="#ce9178")
        # Keyword style
        self.preview_text.tag_configure("keyword", foreground="#569cd6")
        # Function/class style
        self.preview_text.tag_configure("function", foreground="#dcdcaa")
        # Number style
        self.preview_text.tag_configure("number", foreground="#b5cea8")
        # Operator style
        self.preview_text.tag_configure("operator", foreground="#d4d4d4")
    
    def _apply_syntax_highlighting(self, text, file_type):
        """Apply syntax highlighting to preview text"""
        # Clear existing tags
        self.preview_text.tag_remove("comment", "1.0", tk.END)
        self.preview_text.tag_remove("string", "1.0", tk.END)
        self.preview_text.tag_remove("keyword", "1.0", tk.END)
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_start = f"{i+1}.0"
            line_end = f"{i+1}.end"
            
            # Comments
            if file_type in ["python", "file"] and line.strip().startswith('#'):
                self.preview_text.tag_add("comment", line_start, line_end)
            elif file_type in ["javascript", "java", "c", "cpp"] and line.strip().startswith('//'):
                self.preview_text.tag_add("comment", line_start, line_end)
            
            # Simple keyword highlighting for Python
            if file_type == "python":
                keywords = ["import", "from", "def", "class", "if", "else", "elif", 
                           "for", "while", "try", "except", "with", "as", "return"]
                for keyword in keywords:
                    start = 0
                    while True:
                        pos = line.find(keyword, start)
                        if pos == -1:
                            break
                        # Check if it's a whole word
                        if (pos == 0 or not line[pos-1].isalnum()) and \
                           (pos + len(keyword) >= len(line) or not line[pos + len(keyword)].isalnum()):
                            tag_start = f"{i+1}.{pos}"
                            tag_end = f"{i+1}.{pos + len(keyword)}"
                            self.preview_text.tag_add("keyword", tag_start, tag_end)
                        start = pos + 1
    
    def edit_header_format(self):
        """Allow user to edit the header format"""
        if not self.selected_files:
            messagebox.showinfo("No Selection", "Please select a file first.")
            return
        
        # Get first selected file
        filepath = next(iter(self.selected_files))
        info = self.current_scan_results.get(filepath, {})
        
        dialog = tk.Toplevel(self)
        dialog.title("Edit Header Format")
        dialog.geometry("500x200")
        
        ttk.Label(dialog, text="Edit the expected header format:").pack(pady=10)
        
        header_var = tk.StringVar(value=info.get("expected_header", ""))
        entry = ttk.Entry(dialog, textvariable=header_var, width=60)
        entry.pack(pady=5, padx=20, fill="x")
        
        ttk.Label(dialog, text="File: " + os.path.basename(filepath), 
                 font=('TkDefaultFont', 9)).pack(pady=5)
        
        def apply_format():
            new_header = header_var.get()
            if new_header:
                # Update the expected header for this file
                info["expected_header"] = new_header
                # Check if it now matches
                actual = info.get("actual_header", "")
                info["annotated"] = (actual == new_header)
                info["correct"] = info["annotated"]
                
                # Update display
                self.refresh_tree()
                self.on_tree_select(None)
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Apply", command=apply_format).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)
    
    def scan_project(self):
        """Scan all project directories for annotation status"""
        self.file_tree.delete(*self.file_tree.get_children())
        self.current_scan_results = {}
        self.progress_frame.grid()
        
        def scan_thread():
            all_results = {}
            directories = self.config.get("directories", [])
            
            for i, directory in enumerate(directories):
                self.progress_label.config(
                    text=f"Scanning {directory['name']}..."
                )
                self.progress_bar["value"] = (i / len(directories)) * 100
                
                results = self.manager.scan_directory(
                    directory["directory"],
                    directory.get("is_remote", False)
                )
                
                for filepath, status in results.items():
                    all_results[filepath] = {
                        **status,
                        "directory": directory["name"],
                        "is_remote": directory.get("is_remote", False)
                    }
            
            self.after(0, self._update_scan_results, all_results)
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def _update_scan_results(self, results):
        """Update UI with scan results"""
        self.current_scan_results = results
        self.progress_frame.grid_remove()
        
        # Update statistics
        stats = {
            "total": len(results),
            "annotated": sum(1 for r in results.values() if r["annotated"]),
            "missing": sum(1 for r in results.values() if not r["annotated"])
        }
        stats["percentage"] = (stats["annotated"] / stats["total"] * 100) if stats["total"] > 0 else 0
        
        self.stats_labels["total"].config(text=str(stats["total"]))
        self.stats_labels["annotated"].config(text=str(stats["annotated"]))
        self.stats_labels["missing"].config(text=str(stats["missing"]))
        self.stats_labels["percentage"].config(text=f"{stats['percentage']:.1f}%")
        
        self.coverage_progress["value"] = stats["percentage"]
        
        # Update last scan time
        self.last_scan_label.config(
            text=f"Last scan: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        # Populate tree
        self.refresh_tree()
    
    def refresh_tree(self):
        """Refresh the file tree based on current filter"""
        self.file_tree.delete(*self.file_tree.get_children())
        
        filter_mode = self.filter_var.get()
        
        # Group by directory
        by_directory = {}
        for filepath, info in self.current_scan_results.items():
            if filter_mode == "missing" and info["annotated"]:
                continue
            elif filter_mode == "annotated" and not info["annotated"]:
                continue
            
            directory = info["directory"]
            if directory not in by_directory:
                by_directory[directory] = []
            by_directory[directory].append((filepath, info))
        
        # Populate tree
        for directory, files in sorted(by_directory.items()):
            dir_node = self.file_tree.insert("", "end", text=f"📁 {directory}",
                                           values=("", "", ""))
            
            for filepath, info in sorted(files):
                filename = os.path.basename(filepath)
                status = "✅" if info["annotated"] else "❌"
                status_text = "Annotated" if info["annotated"] else "Missing"
                expected_header = info.get("expected_header", "")
                
                self.file_tree.insert(dir_node, "end", 
                                    text=filename,
                                    values=(status_text, info["type"], expected_header),
                                    tags=("annotated" if info["annotated"] else "missing",))
        
        # Configure tags
        self.file_tree.tag_configure("annotated", foreground="green")
        self.file_tree.tag_configure("missing", foreground="red")
        
        # Expand all directories
        for child in self.file_tree.get_children():
            self.file_tree.item(child, open=True)
    
    def on_tree_select(self, event):
        """Handle tree selection changes"""
        selected = self.file_tree.selection()
        self.selected_files.clear()
        
        # Clear preview if nothing selected
        if not selected:
            self.expected_header_var.set("")
            self.current_header_var.set("")
            self.preview_text.config(state="normal")
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.config(state="disabled")
            self.selection_label.config(text="0 files selected")
            self.annotate_selected_btn.config(state="disabled")
            return
        
        # Collect selected files and update preview for first selected
        first_file = None
        for item in selected:
            item_values = self.file_tree.item(item, "values")
            if item_values and len(item_values) > 2:  # File item
                # Find the filepath from scan results
                item_text = self.file_tree.item(item, "text")
                for filepath, info in self.current_scan_results.items():
                    if os.path.basename(filepath) == item_text:
                        self.selected_files.add(filepath)
                        if first_file is None:
                            first_file = (filepath, info)
                        break
        
        # Update UI
        count = len(self.selected_files)
        self.selection_label.config(text=f"{count} file{'s' if count != 1 else ''} selected")
        self.annotate_selected_btn.config(state="normal" if count > 0 else "disabled")
        
        # Update preview for first selected file
        if first_file:
            filepath, info = first_file
            
            # Update header info
            self.expected_header_var.set(info.get("expected_header", ""))
            actual_header = info.get("actual_header", "")
            if actual_header:
                self.current_header_var.set(actual_header)
            else:
                self.current_header_var.set("(No annotation found)")
            
            # Update code preview
            self.preview_text.config(state="normal")
            self.preview_text.delete("1.0", tk.END)
            
            # Show first 4 lines
            first_lines = info.get("first_lines", [])
            if first_lines:
                preview_text = '\n'.join(first_lines[:4])
                self.preview_text.insert("1.0", preview_text)
                
                # Apply syntax highlighting
                file_type = info.get("type", "file")
                self._apply_syntax_highlighting(preview_text, file_type)
            else:
                self.preview_text.insert("1.0", "(Unable to read file)")
            
            self.preview_text.config(state="disabled")
    
    def select_all(self):
        """Select all visible files"""
        for child in self.file_tree.get_children():
            for subchild in self.file_tree.get_children(child):
                self.file_tree.selection_add(subchild)
    
    def select_none(self):
        """Clear selection"""
        self.file_tree.selection_remove(self.file_tree.selection())
    
    def annotate_selected(self):
        """Annotate selected files"""
        if not self.selected_files:
            return
        
        self.progress_frame.grid()
        
        def annotate_thread():
            files_by_remote = {"local": [], "remote": []}
            
            for filepath in self.selected_files:
                info = self.current_scan_results.get(filepath, {})
                if info.get("is_remote"):
                    files_by_remote["remote"].append(filepath)
                else:
                    files_by_remote["local"].append(filepath)
            
            all_files = files_by_remote["local"] + files_by_remote["remote"]
            total = len(all_files)
            success_count = 0
            
            def progress_callback(current, total, message):
                self.after(0, self._update_progress, current, total, message)
            
            # Annotate local files
            if files_by_remote["local"]:
                results = self.manager.annotate_files(
                    files_by_remote["local"], 
                    is_remote=False,
                    progress_callback=progress_callback,
                    scan_results=self.current_scan_results
                )
                success_count += sum(results.values())
            
            # Annotate remote files
            if files_by_remote["remote"]:
                results = self.manager.annotate_files(
                    files_by_remote["remote"], 
                    is_remote=True,
                    progress_callback=progress_callback,
                    scan_results=self.current_scan_results
                )
                success_count += sum(results.values())
            
            self.after(0, self._annotation_complete, success_count, total)
        
        threading.Thread(target=annotate_thread, daemon=True).start()
    
    def annotate_all_missing(self):
        """Annotate all files missing annotations"""
        missing_files = [
            filepath for filepath, info in self.current_scan_results.items()
            if not info["annotated"]
        ]
        
        if not missing_files:
            messagebox.showinfo("No Missing Annotations", 
                              "All files are already annotated!")
            return
        
        if messagebox.askyesno("Confirm Annotation", 
                             f"Annotate {len(missing_files)} files?"):
            self.selected_files = set(missing_files)
            self.annotate_selected()
    
    def verify_annotations(self):
        """Verify existing annotations are correct"""
        # TODO: Implement verification logic
        messagebox.showinfo("Verify Annotations", 
                          "This feature will check if existing annotations match expected paths.")
    
    def preview_annotation(self):
        """Preview what annotation will be added"""
        if not self.selected_files:
            messagebox.showinfo("No Selection", "Please select a file to preview.")
            return
        
        filepath = next(iter(self.selected_files))
        info = self.current_scan_results.get(filepath, {})
        
        expected_header = info.get("expected_header")
        if expected_header:
            prefix, suffix = comment_symbols(os.path.basename(filepath))
            annotation = f"{prefix} {expected_header}{suffix}"
            
            current_header = info.get("actual_header", "(No current annotation)")
            
            preview_text = f"File: {os.path.basename(filepath)}\n\n"
            preview_text += f"Current annotation:\n{current_header}\n\n"
            preview_text += f"Will be replaced with:\n{annotation}"
            
            messagebox.showinfo("Annotation Preview", preview_text)
        else:
            messagebox.showwarning("Preview Error", "Could not determine expected header format.")
    
    def _update_progress(self, current, total, message):
        """Update progress display"""
        self.progress_label.config(text=message)
        self.progress_bar["value"] = (current / total * 100) if total > 0 else 0
        self.update_idletasks()
    
    def _annotation_complete(self, success_count, total):
        """Handle annotation completion"""
        self.progress_frame.grid_remove()
        
        messagebox.showinfo("Annotation Complete", 
                          f"Successfully annotated {success_count} of {total} files.")
        
        # Refresh the scan
        self.scan_project()