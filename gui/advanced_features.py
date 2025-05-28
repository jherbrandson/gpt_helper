# gpt_helper/dev/gui/advanced_features.py
"""
Additional advanced features for GPT Helper
"""
import os
import re
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import difflib
from collections import defaultdict

class FilePreviewWidget(ttk.Frame):
    """
    Live file preview with syntax highlighting
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.current_file = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the preview UI"""
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=5, pady=5)
        
        self.file_label = ttk.Label(header, text="No file selected", font=("Arial", 10, "bold"))
        self.file_label.pack(side="left")
        
        self.size_label = ttk.Label(header, text="", foreground="gray")
        self.size_label.pack(side="right")
        
        # Preview area with syntax highlighting
        self.preview_text = tk.Text(self, wrap="none", height=20, width=60,
                                   bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self.preview_text.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        
        # Scrollbars
        vsb = ttk.Scrollbar(self.preview_text, orient="vertical", command=self.preview_text.yview)
        hsb = ttk.Scrollbar(self.preview_text, orient="horizontal", command=self.preview_text.xview)
        self.preview_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Configure syntax highlighting tags
        self._setup_syntax_tags()
        
        # Make read-only
        self.preview_text.bind("<Key>", lambda e: "break")
    
    def _setup_syntax_tags(self):
        """Setup syntax highlighting tags"""
        # Python syntax
        self.preview_text.tag_configure("keyword", foreground="#569cd6")
        self.preview_text.tag_configure("string", foreground="#ce9178")
        self.preview_text.tag_configure("comment", foreground="#6a9955")
        self.preview_text.tag_configure("function", foreground="#dcdcaa")
        self.preview_text.tag_configure("number", foreground="#b5cea8")
        self.preview_text.tag_configure("class", foreground="#4ec9b0")
        
        # Line numbers
        self.preview_text.tag_configure("linenumber", foreground="#858585", background="#2d2d2d")
    
    def preview_file(self, filepath, content=None):
        """Preview a file with syntax highlighting"""
        self.current_file = filepath
        self.file_label.config(text=os.path.basename(filepath))
        
        # Clear previous content
        self.preview_text.delete("1.0", tk.END)
        
        try:
            # Get content if not provided
            if content is None:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            # Limit preview size
            lines = content.splitlines()[:100]
            if len(content.splitlines()) > 100:
                lines.append("... (truncated)")
            
            # Get file size
            size = len(content)
            self.size_label.config(text=f"{size:,} bytes")
            
            # Apply syntax highlighting based on file type
            ext = os.path.splitext(filepath)[1].lower()
            
            if ext in ['.py', '.pyw']:
                self._highlight_python(lines)
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                self._highlight_javascript(lines)
            elif ext in ['.json']:
                self._highlight_json(lines)
            else:
                # Plain text
                for i, line in enumerate(lines, 1):
                    self.preview_text.insert(tk.END, f"{i:4d} │ {line}\n")
                    self.preview_text.tag_add("linenumber", f"{i}.0", f"{i}.6")
        
        except Exception as e:
            self.preview_text.insert("1.0", f"Error reading file: {e}")
            self.size_label.config(text="Error")
    
    def _highlight_python(self, lines):
        """Apply Python syntax highlighting"""
        python_keywords = {
            'def', 'class', 'import', 'from', 'as', 'if', 'elif', 'else',
            'for', 'while', 'try', 'except', 'finally', 'with', 'return',
            'yield', 'lambda', 'and', 'or', 'not', 'in', 'is', 'None',
            'True', 'False', 'self', 'async', 'await', 'pass', 'break',
            'continue', 'global', 'nonlocal', 'assert', 'del'
        }
        
        for i, line in enumerate(lines, 1):
            # Insert line with line number
            line_start = self.preview_text.index(tk.END)
            self.preview_text.insert(tk.END, f"{i:4d} │ {line}\n")
            
            # Tag line number
            self.preview_text.tag_add("linenumber", f"{i}.0", f"{i}.6")
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Comments
            if '#' in line:
                comment_start = line.index('#')
                self.preview_text.tag_add("comment", f"{i}.{comment_start + 7}", f"{i}.end")
            
            # Strings
            for match in re.finditer(r'(["\'])(?:(?=(\\?))\2.)*?\1', line):
                start, end = match.span()
                self.preview_text.tag_add("string", f"{i}.{start + 7}", f"{i}.{end + 7}")
            
            # Keywords
            for word in python_keywords:
                for match in re.finditer(r'\b' + word + r'\b', line):
                    start, end = match.span()
                    self.preview_text.tag_add("keyword", f"{i}.{start + 7}", f"{i}.{end + 7}")
            
            # Functions
            for match in re.finditer(r'\bdef\s+(\w+)', line):
                start, end = match.span(1)
                self.preview_text.tag_add("function", f"{i}.{start + 7}", f"{i}.{end + 7}")
            
            # Classes
            for match in re.finditer(r'\bclass\s+(\w+)', line):
                start, end = match.span(1)
                self.preview_text.tag_add("class", f"{i}.{start + 7}", f"{i}.{end + 7}")

class SmartSelectionDialog(tk.Toplevel):
    """
    Advanced selection dialog with multiple criteria
    """
    def __init__(self, parent, file_tree_widget):
        super().__init__(parent)
        self.file_tree_widget = file_tree_widget
        self.title("Smart Selection")
        self.geometry("500x600")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the smart selection UI"""
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Pattern-based selection
        self.setup_pattern_tab(notebook)
        
        # Size-based selection
        self.setup_size_tab(notebook)
        
        # Date-based selection
        self.setup_date_tab(notebook)
        
        # Content-based selection
        self.setup_content_tab(notebook)
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Apply", command=self.apply_selection).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")
    
    def setup_pattern_tab(self, notebook):
        """Setup pattern-based selection tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="File Patterns")
        
        ttk.Label(frame, text="Select files matching patterns:").pack(anchor="w", padx=10, pady=10)
        
        # Common patterns
        self.pattern_vars = {}
        patterns = [
            ("Python files", "*.py"),
            ("Test files", "*test*.py"),
            ("JavaScript/TypeScript", "*.js,*.jsx,*.ts,*.tsx"),
            ("Configuration", "*.json,*.yaml,*.yml,*.toml"),
            ("Documentation", "*.md,*.rst,*.txt"),
            ("Hidden files", ".*"),
        ]
        
        for label, pattern in patterns:
            var = tk.BooleanVar()
            self.pattern_vars[pattern] = var
            ttk.Checkbutton(frame, text=f"{label} ({pattern})", 
                           variable=var).pack(anchor="w", padx=20, pady=2)
        
        # Custom pattern
        ttk.Label(frame, text="Custom patterns (comma-separated):").pack(anchor="w", padx=10, pady=(20, 5))
        self.custom_pattern = tk.StringVar()
        ttk.Entry(frame, textvariable=self.custom_pattern, width=40).pack(padx=20, pady=5)
        
        # Options
        self.pattern_recursive = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Apply recursively to subdirectories",
                       variable=self.pattern_recursive).pack(anchor="w", padx=20, pady=10)
    
    def setup_size_tab(self, notebook):
        """Setup size-based selection tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="File Size")
        
        ttk.Label(frame, text="Select files based on size:").pack(anchor="w", padx=10, pady=10)
        
        # Size criteria
        size_frame = ttk.Frame(frame)
        size_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(size_frame, text="Minimum size:").grid(row=0, column=0, sticky="w", pady=5)
        self.min_size = tk.StringVar(value="0")
        ttk.Entry(size_frame, textvariable=self.min_size, width=15).grid(row=0, column=1, padx=5)
        
        self.min_unit = tk.StringVar(value="KB")
        ttk.Combobox(size_frame, textvariable=self.min_unit, 
                    values=["B", "KB", "MB", "GB"], width=5).grid(row=0, column=2)
        
        ttk.Label(size_frame, text="Maximum size:").grid(row=1, column=0, sticky="w", pady=5)
        self.max_size = tk.StringVar(value="10")
        ttk.Entry(size_frame, textvariable=self.max_size, width=15).grid(row=1, column=1, padx=5)
        
        self.max_unit = tk.StringVar(value="MB")
        ttk.Combobox(size_frame, textvariable=self.max_unit,
                    values=["B", "KB", "MB", "GB"], width=5).grid(row=1, column=2)
        
        # Presets
        ttk.Label(frame, text="Quick presets:").pack(anchor="w", padx=10, pady=(20, 5))
        
        preset_frame = ttk.Frame(frame)
        preset_frame.pack(fill="x", padx=20)
        
        presets = [
            ("Small files (< 10KB)", lambda: self.set_size_range(0, 10, "KB")),
            ("Medium files (10KB - 1MB)", lambda: self.set_size_range(10, 1, "KB", "MB")),
            ("Large files (> 1MB)", lambda: self.set_size_range(1, 9999, "MB", "GB")),
        ]
        
        for label, command in presets:
            ttk.Button(preset_frame, text=label, command=command).pack(pady=2, fill="x")
    
    def setup_date_tab(self, notebook):
        """Setup date-based selection tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Modified Date")
        
        ttk.Label(frame, text="Select files based on modification date:").pack(anchor="w", padx=10, pady=10)
        
        # Date options
        self.date_option = tk.StringVar(value="days")
        
        options = [
            ("Modified in last N days", "days"),
            ("Modified after specific date", "after"),
            ("Modified before specific date", "before"),
            ("Modified between dates", "between"),
        ]
        
        for label, value in options:
            ttk.Radiobutton(frame, text=label, variable=self.date_option,
                           value=value).pack(anchor="w", padx=20, pady=5)
        
        # Days input
        days_frame = ttk.Frame(frame)
        days_frame.pack(fill="x", padx=40, pady=10)
        
        ttk.Label(days_frame, text="Days:").pack(side="left")
        self.days_value = tk.StringVar(value="7")
        ttk.Entry(days_frame, textvariable=self.days_value, width=10).pack(side="left", padx=5)
        
        # Date inputs (simplified for demo)
        date_frame = ttk.Frame(frame)
        date_frame.pack(fill="x", padx=40, pady=10)
        
        ttk.Label(date_frame, text="Date (YYYY-MM-DD):").pack(anchor="w")
        self.date_value = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(date_frame, textvariable=self.date_value, width=15).pack(anchor="w", pady=5)
    
    def setup_content_tab(self, notebook):
        """Setup content-based selection tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="File Content")
        
        ttk.Label(frame, text="Select files containing specific content:").pack(anchor="w", padx=10, pady=10)
        
        # Search terms
        ttk.Label(frame, text="Search for:").pack(anchor="w", padx=10, pady=5)
        self.content_search = tk.Text(frame, height=5, width=50)
        self.content_search.pack(padx=20, pady=5)
        
        # Options
        self.content_case_sensitive = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Case sensitive",
                       variable=self.content_case_sensitive).pack(anchor="w", padx=20, pady=5)
        
        self.content_regex = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Use regular expressions",
                       variable=self.content_regex).pack(anchor="w", padx=20, pady=5)
        
        # File type filter
        ttk.Label(frame, text="Only search in files matching:").pack(anchor="w", padx=10, pady=(20, 5))
        self.content_file_pattern = tk.StringVar(value="*.py,*.js,*.txt,*.md")
        ttk.Entry(frame, textvariable=self.content_file_pattern, width=40).pack(padx=20, pady=5)
        
        # Warning
        warning_label = ttk.Label(frame, text="⚠️ Content search may be slow for large projects",
                                 foreground="orange")
        warning_label.pack(anchor="w", padx=10, pady=10)
    
    def set_size_range(self, min_val, max_val, min_unit="KB", max_unit="MB"):
        """Set size range preset"""
        self.min_size.set(str(min_val))
        self.max_size.set(str(max_val))
        self.min_unit.set(min_unit)
        self.max_unit.set(max_unit)
    
    def apply_selection(self):
        """Apply the smart selection criteria"""
        # This would integrate with the file tree widget
        # to select files based on the criteria
        messagebox.showinfo("Smart Selection", 
                           "Smart selection would be applied here based on your criteria")
        self.destroy()

class ProjectAnalyzer:
    """
    Analyze project structure and provide insights
    """
    def __init__(self, base_dir, blacklist=None):
        self.base_dir = base_dir
        self.blacklist = blacklist or {}
        self.stats = defaultdict(int)
        self.file_types = defaultdict(list)
        
    def analyze(self):
        """Analyze the project structure"""
        self.stats.clear()
        self.file_types.clear()
        
        for root, dirs, files in os.walk(self.base_dir):
            # Skip blacklisted directories
            dirs[:] = [d for d in dirs if not self._is_blacklisted(os.path.join(root, d))]
            
            self.stats['directories'] += 1
            
            for file in files:
                filepath = os.path.join(root, file)
                if self._is_blacklisted(filepath):
                    continue
                
                self.stats['files'] += 1
                
                # File extension analysis
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    self.file_types[ext].append(filepath)
                    self.stats[f'files_{ext}'] += 1
                
                # Size analysis
                try:
                    size = os.path.getsize(filepath)
                    self.stats['total_size'] += size
                    
                    if size == 0:
                        self.stats['empty_files'] += 1
                    elif size < 1024:
                        self.stats['tiny_files'] += 1
                    elif size < 10240:
                        self.stats['small_files'] += 1
                    elif size < 1048576:
                        self.stats['medium_files'] += 1
                    else:
                        self.stats['large_files'] += 1
                except:
                    pass
        
        return self.get_report()
    
    def _is_blacklisted(self, path):
        """Check if path is blacklisted"""
        # Implementation would check against blacklist
        return False
    
    def get_report(self):
        """Generate analysis report"""
        report = []
        report.append(f"Project Analysis: {os.path.basename(self.base_dir)}")
        report.append("=" * 50)
        report.append(f"Total directories: {self.stats['directories']:,}")
        report.append(f"Total files: {self.stats['files']:,}")
        report.append(f"Total size: {self._format_size(self.stats['total_size'])}")
        report.append("")
        
        # File type distribution
        report.append("File Types:")
        sorted_types = sorted(self.file_types.items(), 
                            key=lambda x: len(x[1]), reverse=True)[:10]
        
        for ext, files in sorted_types:
            percentage = len(files) / self.stats['files'] * 100
            report.append(f"  {ext}: {len(files)} files ({percentage:.1f}%)")
        
        report.append("")
        report.append("Size Distribution:")
        report.append(f"  Empty: {self.stats['empty_files']}")
        report.append(f"  Tiny (<1KB): {self.stats['tiny_files']}")
        report.append(f"  Small (1-10KB): {self.stats['small_files']}")
        report.append(f"  Medium (10KB-1MB): {self.stats['medium_files']}")
        report.append(f"  Large (>1MB): {self.stats['large_files']}")
        
        # Recommendations
        report.append("")
        report.append("Recommendations:")
        
        if self.stats['large_files'] > 10:
            report.append("  • Consider blacklisting large files to improve performance")
        
        if self.stats['empty_files'] > 20:
            report.append("  • Many empty files detected - consider cleanup")
        
        # Most common file types
        if sorted_types:
            most_common = sorted_types[0][0]
            report.append(f"  • Use quick filter for {most_common} files (most common type)")
        
        return "\n".join(report)
    
    def _format_size(self, size):
        """Format size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

class SessionManager:
    """
    Manage multiple selection sessions/profiles
    """
    def __init__(self, config_dir=None):
        self.config_dir = config_dir or "gpt_helper_sessions"
        os.makedirs(self.config_dir, exist_ok=True)
        
    def save_session(self, name, data):
        """Save a selection session"""
        filepath = os.path.join(self.config_dir, f"{name}.json")
        
        session_data = {
            'name': name,
            'created': datetime.now().isoformat(),
            'data': data,
            'version': '1.0'
        }
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
    
    def load_session(self, name):
        """Load a selection session"""
        filepath = os.path.join(self.config_dir, f"{name}.json")
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    
    def list_sessions(self):
        """List all saved sessions"""
        sessions = []
        
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.config_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        sessions.append({
                            'name': data.get('name', filename[:-5]),
                            'created': data.get('created', 'Unknown'),
                            'file_count': len(data.get('data', {}).get('selected_files', [])),
                            'filename': filename
                        })
                except:
                    pass
        
        return sorted(sessions, key=lambda x: x['created'], reverse=True)
    
    def delete_session(self, name):
        """Delete a session"""
        filepath = os.path.join(self.config_dir, f"{name}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

def integrate_advanced_features(tree_widget):
    """
    Integrate advanced features into existing tree widget
    """
    # Add preview pane
    if hasattr(tree_widget, 'master'):
        preview_frame = ttk.Frame(tree_widget.master)
        preview_widget = FilePreviewWidget(preview_frame)
        
        # Bind tree selection to preview
        def on_tree_select(event):
            selection = tree_widget.tree.selection()
            if selection and len(selection) == 1:
                item = selection[0]
                if item in tree_widget.item_to_node:
                    node = tree_widget.item_to_node[item]
                    if not node.is_dir:
                        preview_widget.preview_file(node.path)
        
        tree_widget.tree.bind('<<TreeviewSelect>>', on_tree_select)
    
    # Add smart selection button
    if hasattr(tree_widget, 'action_frame'):
        smart_btn = ttk.Button(tree_widget.action_frame, 
                              text="Smart Select...",
                              command=lambda: SmartSelectionDialog(tree_widget, tree_widget))
        smart_btn.pack(side="left", padx=5)
    
    # Add project analysis
    def show_analysis():
        analyzer = ProjectAnalyzer(tree_widget.base_dir, tree_widget.blacklist)
        report = analyzer.analyze()
        
        # Show in dialog
        dialog = tk.Toplevel(tree_widget)
        dialog.title("Project Analysis")
        dialog.geometry("600x500")
        
        text = tk.Text(dialog, wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", report)
        text.config(state="disabled")
        
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    # Add to menu or toolbar
    if hasattr(tree_widget, 'master'):
        analysis_btn = ttk.Button(tree_widget, text="Analyze Project", command=show_analysis)
        analysis_btn.pack(side="bottom", pady=5)
    
    return tree_widget