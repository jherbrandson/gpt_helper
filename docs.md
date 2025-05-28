╔══════════════════════════════════════════════════════════════════╗
║                  GPT HELPER IMPROVED - QUICK REFERENCE            ║
╚══════════════════════════════════════════════════════════════════╝

COMMAND LINE
────────────
python main_improved.py          # Normal run with GUI
python main_improved.py --quick  # Skip GUI, use last selection  
python main_improved.py --step1  # Preview Step 1 only
python main_improved.py --stats  # Show project statistics
python main_improved.py --clear-cache  # Clear all caches
python main_improved.py -e all   # Edit all config files
python main_improved.py -e background.txt  # Edit specific file

GUI KEYBOARD SHORTCUTS
──────────────────────
Ctrl+A         Select all visible files
Space          Toggle selection on focused items
Double-click   Toggle file/directory (+ Shift for recursive)
Tab            Switch between GUI tabs

FILE SELECTION TAB
──────────────────
[ ]  Unselected file/directory
[✓]  Selected file/directory
/    Directory indicator
🔍   Filter box for searching

Buttons:
• Select All      - Select all visible files
• Deselect All    - Clear all selections
• Select Filtered - Select only filtered matches
• Expand All      - Open all directories
• Collapse All    - Close all directories

BLACKLIST TAB  
─────────────
[B]  Blacklisted item (red background)
Double-click to toggle blacklist status
Blacklisted directories don't load contents (performance!)

Buttons:
• Clear All    - Remove all blacklist entries
• Expand All   - Show full tree
• Collapse All - Collapse to root

ADDITIONAL FILES TAB
────────────────────
Left pane:  Available files (not selected)
Right pane: Selected additional files
✓ in tree:  File already selected

These files appear at end of Step 1 output
Perfect for: .env, docker-compose.yml, README.md

Buttons:
• Add →        - Add selected files
• ← Remove     - Remove selected files  
• Add All →    - Add all visible files
• ← Remove All - Clear all selections

CONFIG FILES TAB
────────────────
Edit without leaving GUI:
• background.txt   - Project overview
• rules.txt        - Coding standards
• current_goal.txt - Current objectives

OUTPUT STRUCTURE
────────────────
Step 1: Project info
  • Background text
  • Directory tree
  • Rules text
  • Current goal
  • Additional files (if enabled)

Step 2: Selected source files
  • All files from File Selection tab

PERFORMANCE TIPS
────────────────
Remote:
• First run builds cache (be patient)
• Use --quick for subsequent runs
• Clear cache only when needed

Large Projects:
• Blacklist node_modules, .git, venv early
• Use filter instead of scrolling
• Toggle additional files based on task

STATUS INDICATORS
─────────────────
"Files: 25/150 selected (45 visible)"
  │      │              │
  │      │              └─ Shown when filtering
  │      └─ Total files in project
  └─ Currently selected files

"Blacklist contains 3 items"
"4 additional files selected"
"Additional files disabled"

COMMON WORKFLOWS
────────────────
Feature Development:
1. Disable additional files
2. Select only relevant source
3. Use --quick for iterations

Config/Infrastructure:
1. Enable additional files
2. Add .env, docker-compose.yml
3. Select deployment scripts

Documentation:
1. Enable additional files  
2. Add README.md, docs/*
3. Select relevant code files

TROUBLESHOOTING
───────────────
Slow GUI:
→ Blacklist large directories
→ Clear cache if remote changed
→ Use filter to reduce visible items

Missing files:
→ Check blacklist settings
→ Expand parent directories
→ Clear filter if active

Import errors:
→ Ensure gui_improved.py exists
→ Check Python path includes current dir