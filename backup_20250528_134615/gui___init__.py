"""
Improved GUI package for GPT Helper
"""
# Try to import enhanced components
try:
    from .file_selection_enhanced import ImprovedFileSelectionWidget
    from .main_enhanced import EnhancedFileSelectionGUI, enhanced_gui_selection
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False

# Import standard components
from .main import gui_selection, ImprovedFileSelectionGUI
from .base import load_selection_state, save_selection_state, remote_cache

# Export appropriate version
if ENHANCED_AVAILABLE:
    __all__ = [
        'gui_selection',
        'ImprovedFileSelectionGUI',
        'EnhancedFileSelectionGUI',
        'enhanced_gui_selection',
        'ImprovedFileSelectionWidget',
        'load_selection_state',
        'save_selection_state',
        'remote_cache',
        'ENHANCED_AVAILABLE'
    ]
else:
    __all__ = [
        'gui_selection',
        'ImprovedFileSelectionGUI',
        'load_selection_state',
        'save_selection_state',
        'remote_cache',
        'ENHANCED_AVAILABLE'
    ]
