# gpt_helper/dev/integrate_enhanced_setup.py
#!/usr/bin/env python
"""
Complete integration script for enhanced GPT Helper setup
This script properly integrates all enhanced features and fixes module issues.
"""
import os
import sys
import shutil
import json
from datetime import datetime

def create_backup(base_dir):
    """Create backup of existing setup files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(base_dir, "trash", f"setup_backup_{timestamp}")
    
    os.makedirs(backup_dir, exist_ok=True)
    
    # Files to backup
    files_to_backup = [
        "main.py",
        "setup/__init__.py",
        "setup/overall_setup.py",
        "setup/directory_config.py",
        "setup/blacklist_setup.py",
        "setup/content_setup.py"
    ]
    
    backed_up = []
    for file_path in files_to_backup:
        src = os.path.join(base_dir, file_path)
        if os.path.exists(src):
            dst = os.path.join(backup_dir, file_path.replace("/", "_"))
            try:
                shutil.copy2(src, dst)
                backed_up.append(file_path)
                print(f"  ✅ Backed up {file_path}")
            except Exception as e:
                print(f"  ⚠️  Failed to backup {file_path}: {e}")
    
    return backup_dir, backed_up

def update_setup_init(base_dir):
    """Update setup/__init__.py with proper imports"""
    init_path = os.path.join(base_dir, "setup", "__init__.py")
    
    init_content = '''# gpt_helper/dev/setup/__init__.py
"""
Enhanced setup module for GPT Helper
"""
import os
import sys

# Ensure the parent directory is in the path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import enhanced components with error handling
ENHANCED_SETUP_AVAILABLE = False

try:
    from .wizard_base import SetupWizard, WizardStep, create_info_box, create_field_with_validation
    from .overall_setup_enhanced import OverallSetupStep
    from .directory_config_enhanced import DirectoryConfigStep
    from .blacklist_setup_enhanced import BlacklistSetupStep
    from .content_setup_enhanced import ContentSetupStep
    from .enhanced_setup import enhance_wizard, ProjectAnalyzer, SetupSessionManager
    from .run_enhanced_setup import run_enhanced_setup
    
    ENHANCED_SETUP_AVAILABLE = True
    print("✅ Enhanced setup components loaded successfully")
    
except ImportError as e:
    print(f"⚠️  Enhanced setup not fully available: {e}")

# Always import classic setup functions for compatibility
try:
    from .overall_setup import run_directory_setup
    from .directory_config import run_directory_config
    from .blacklist_setup import run_blacklist_setup
    from .content_setup import run_content_setup
except ImportError as e:
    print(f"❌ Error importing classic setup: {e}")

# Export main setup function
def run_setup(enhanced=None):
    """
    Run the setup wizard
    
    Args:
        enhanced: If True, use enhanced wizard. If False, use classic wizard.
                 If None, auto-detect based on availability.
    """
    if enhanced is None:
        enhanced = ENHANCED_SETUP_AVAILABLE
    
    if enhanced and ENHANCED_SETUP_AVAILABLE:
        try:
            return run_enhanced_setup()
        except Exception as e:
            print(f"⚠️  Enhanced setup failed: {e}")
            print("   Falling back to classic setup...")
            enhanced = False
    
    if not enhanced:
        # Classic setup fallback
        try:
            # Import here to avoid circular imports
            import main
            return main.run_config_setup()
        except Exception as e:
            print(f"❌ Classic setup also failed: {e}")
            raise

__all__ = [
    'run_setup',
    'run_directory_setup',
    'run_directory_config', 
    'run_blacklist_setup',
    'run_content_setup',
    'ENHANCED_SETUP_AVAILABLE'
]

if ENHANCED_SETUP_AVAILABLE:
    __all__.extend([
        'SetupWizard',
        'WizardStep',
        'create_info_box',
        'create_field_with_validation',
        'OverallSetupStep',
        'DirectoryConfigStep',
        'BlacklistSetupStep',
        'ContentSetupStep',
        'enhance_wizard',
        'ProjectAnalyzer',
        'SetupSessionManager',
        'run_enhanced_setup'
    ])
'''
    
    try:
        with open(init_path, 'w') as f:
            f.write(init_content)
        return True
    except Exception as e:
        print(f"❌ Failed to update setup/__init__.py: {e}")
        return False

def create_test_script(base_dir):
    """Create a test script to verify the enhanced setup"""
    test_content = '''#!/usr/bin/env python
# gpt_helper/dev/test_enhanced_setup.py
"""
Test script for enhanced setup integration
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🧪 Testing Enhanced Setup Integration")
print("="*60)

# Test 1: Import setup module
print("\\n📋 Test 1: Import setup module")
try:
    import setup
    print("  ✅ setup module imported successfully")
    print(f"  📍 Module location: {setup.__file__}")
except ImportError as e:
    print(f"  ❌ Failed to import setup: {e}")
    sys.exit(1)

# Test 2: Check enhanced availability
print("\\n📋 Test 2: Check enhanced setup availability")
try:
    from setup import ENHANCED_SETUP_AVAILABLE
    if ENHANCED_SETUP_AVAILABLE:
        print("  ✅ Enhanced setup is available")
    else:
        print("  ⚠️  Enhanced setup not available (falling back to classic)")
except Exception as e:
    print(f"  ❌ Error checking availability: {e}")

# Test 3: Import enhanced components
if ENHANCED_SETUP_AVAILABLE:
    print("\\n📋 Test 3: Import enhanced components")
    components = [
        ('SetupWizard', 'setup.wizard_base'),
        ('OverallSetupStep', 'setup.overall_setup_enhanced'),
        ('DirectoryConfigStep', 'setup.directory_config_enhanced'),
        ('BlacklistSetupStep', 'setup.blacklist_setup_enhanced'),
        ('ContentSetupStep', 'setup.content_setup_enhanced'),
    ]
    
    all_good = True
    for component, module in components:
        try:
            exec(f"from {module} import {component}")
            print(f"  ✅ {component} imported successfully")
        except Exception as e:
            print(f"  ❌ Failed to import {component}: {e}")
            all_good = False
    
    if all_good:
        print("\\n✅ All enhanced components imported successfully!")
else:
    print("\\n⚠️  Skipping enhanced component tests")

# Test 4: Run setup function
print("\\n📋 Test 4: Test run_setup function")
try:
    from setup import run_setup
    print("  ✅ run_setup function is available")
    print("\\n🎉 Integration test passed! You can now run the enhanced setup.")
except Exception as e:
    print(f"  ❌ run_setup function not available: {e}")

print("\\n" + "="*60)
print("To run the enhanced setup, use:")
print("  python main.py --setup")
print("  OR")
print("  python setup_enhanced.py")
'''
    
    test_path = os.path.join(base_dir, "test_enhanced_setup.py")
    try:
        with open(test_path, 'w') as f:
            f.write(test_content)
        os.chmod(test_path, 0o755)
        return test_path
    except Exception as e:
        print(f"⚠️  Failed to create test script: {e}")
        return None

def create_shortcuts(base_dir):
    """Create convenient shortcut scripts"""
    # Enhanced setup shortcut
    setup_shortcut = '''#!/usr/bin/env python
# gpt_helper/dev/run_enhanced_setup.py
"""
Direct launcher for enhanced setup wizard
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from setup import run_enhanced_setup, ENHANCED_SETUP_AVAILABLE
    
    if ENHANCED_SETUP_AVAILABLE:
        print("🚀 Launching Enhanced GPT Helper Setup...")
        run_enhanced_setup()
    else:
        print("⚠️  Enhanced setup not available, using classic setup...")
        from main import run_config_setup
        run_config_setup()
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\\nTry running: python main.py --setup")
'''
    
    # Config viewer shortcut
    viewer_shortcut = '''#!/usr/bin/env python
# gpt_helper/dev/view_config.py
"""
Launch configuration viewer
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from setup.setup_validator import ConfigurationViewer
    viewer = ConfigurationViewer()
    viewer.show()
except Exception as e:
    print(f"❌ Error launching config viewer: {e}")
'''
    
    shortcuts = [
        ("run_enhanced_setup.py", setup_shortcut),
        ("view_config.py", viewer_shortcut)
    ]
    
    created = []
    for filename, content in shortcuts:
        path = os.path.join(base_dir, filename)
        try:
            with open(path, 'w') as f:
                f.write(content)
            os.chmod(path, 0o755)
            created.append(filename)
        except Exception as e:
            print(f"  ⚠️  Failed to create {filename}: {e}")
    
    return created

def main():
    """Main integration function"""
    print("🔧 GPT Helper Enhanced Setup Integration")
    print("="*60)
    
    # Get base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    # Step 1: Create backup
    print("\\n📦 Creating backup...")
    backup_dir, backed_up = create_backup(base_dir)
    print(f"  ✅ Backup created in: {backup_dir}")
    
    # Step 2: Update setup/__init__.py
    print("\\n📝 Updating setup module...")
    if update_setup_init(base_dir):
        print("  ✅ Updated setup/__init__.py")
    else:
        print("  ❌ Failed to update setup/__init__.py")
        print(f"     Your files are backed up in: {backup_dir}")
        sys.exit(1)
    
    # Step 3: Update main.py if the artifact version exists
    print("\\n📝 Checking for improved main.py...")
    improved_main_exists = os.path.exists(os.path.join(base_dir, "main_improved.py"))
    if improved_main_exists:
        try:
            shutil.copy2("main_improved.py", "main.py")
            print("  ✅ Updated main.py with enhanced version")
        except Exception as e:
            print(f"  ⚠️  Could not update main.py: {e}")
    else:
        print("  ℹ️  Using existing main.py")
    
    # Step 4: Create test script
    print("\\n🧪 Creating test script...")
    test_script = create_test_script(base_dir)
    if test_script:
        print(f"  ✅ Created {test_script}")
    
    # Step 5: Create shortcuts
    print("\\n🔗 Creating shortcuts...")
    shortcuts = create_shortcuts(base_dir)
    for shortcut in shortcuts:
        print(f"  ✅ Created {shortcut}")
    
    # Step 6: Run the test
    print("\\n🧪 Running integration test...")
    print("-"*60)
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, "test_enhanced_setup.py"], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        if result.returncode == 0:
            print("\\n✅ Integration completed successfully!")
            print("\\n📋 Next steps:")
            print("  1. Run the enhanced setup: python run_enhanced_setup.py")
            print("  2. Or use main.py: python main.py --setup")
            print("  3. View/edit config: python view_config.py")
        else:
            print("\\n❌ Integration test failed")
            print(f"   Your files are backed up in: {backup_dir}")
    
    except Exception as e:
        print(f"\\n❌ Error during integration: {e}")
        print(f"   Your files are backed up in: {backup_dir}")

if __name__ == "__main__":
    main()