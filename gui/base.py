# gpt_helper/dev/gui/base.py
"""
Base classes and common functionality for the improved GUI
"""
import os
import json
import tkinter as tk
from tkinter import ttk, font as tkfont
from functools import lru_cache

STATE_SELECTION_FILE = "selection_state.json"
CACHE_FILE = "remote_cache.json"

# ---------------------------------------------------------------------------
# Cache management for remote operations
# ---------------------------------------------------------------------------
class RemoteCache:
    def __init__(self):
        self.cache = {}
        self.load_cache()
    
    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}
    
    def save_cache(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f)
        except:
            pass
    
    def get(self, key, default=None):
        return self.cache.get(key, default)
    
    def set(self, key, value):
        self.cache[key] = value
        self.save_cache()

remote_cache = RemoteCache()

# ---------------------------------------------------------------------------
# Enhanced file tree data structure
# ---------------------------------------------------------------------------
class FileTreeNode:
    def __init__(self, name, path, is_dir=False, parent=None):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.parent = parent
        self.children = []
        self.selected = False
        self.expanded = False
        self.visible = True
        self.matches_filter = True
    
    def toggle_selection(self, recursive=True):
        """Toggle selection state, optionally recursively"""
        self.selected = not self.selected
        if recursive and self.is_dir:
            for child in self.children:
                child.set_selection(self.selected, recursive=True)
    
    def set_selection(self, state, recursive=True):
        """Set selection state, optionally recursively"""
        self.selected = state
        if recursive and self.is_dir:
            for child in self.children:
                child.set_selection(state, recursive=True)
    
    def get_selected_files(self):
        """Get all selected file paths recursively"""
        selected = []
        if not self.is_dir and self.selected:
            selected.append(self.path)
        for child in self.children:
            selected.extend(child.get_selected_files())
        return selected
    
    def apply_filter(self, filter_text):
        """Apply filter and return if this node or any child matches"""
        filter_lower = filter_text.lower()
        name_matches = filter_lower in self.name.lower()
        path_matches = filter_lower in self.path.lower()
        
        # Check if any child matches
        child_matches = False
        for child in self.children:
            if child.apply_filter(filter_text):
                child_matches = True
        
        self.matches_filter = name_matches or path_matches or child_matches
        self.visible = self.matches_filter
        
        # If a child matches, ensure this directory is visible
        if child_matches and self.is_dir:
            self.visible = True
            
        return self.matches_filter

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def load_selection_state():
    if os.path.exists(STATE_SELECTION_FILE):
        try:
            with open(STATE_SELECTION_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading selection state: {e}")
    return {}

def save_selection_state(state):
    try:
        with open(STATE_SELECTION_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving selection state: {e}")

def setup_tree_tags(tree):
    """Setup common tree view tags"""
    default_font = tkfont.nametofont("TkDefaultFont")
    dir_font = default_font.copy()
    dir_font.configure(weight="bold")
    
    tree.tag_configure("directory", font=dir_font, foreground="#0066cc")
    tree.tag_configure("file", foreground="#333333")
    tree.tag_configure("selected", background="#e6f3ff")
    tree.tag_configure("filtered", background="#fffacd")
    tree.tag_configure("blacklisted", background="#ffcccc", font=(default_font, 10, "bold"))