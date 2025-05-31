# gpt_helper/dev/setup/run_consolidated.py
"""
Run the consolidated setup wizard with improved UX
"""
import os
import sys
import json
from setup.wizard_base import SetupWizard
from setup.consolidated_setup import (
    ConsolidatedProjectStep,
    SmartFiltersStep, 
    FinalReviewStep
)

def run_consolidated_setup():
    """Run the new consolidated setup with fewer steps"""
    # Create wizard instance
    wizard = SetupWizard()
    
    # Add only 3 consolidated steps instead of 4
    wizard.add_step(ConsolidatedProjectStep(wizard))
    wizard.add_step(SmartFiltersStep(wizard))
    wizard.add_step(FinalReviewStep(wizard))
    
    # Run wizard
    if wizard.run():
        return wizard.config
    else:
        return None

def run_quick_setup():
    """Ultra-quick setup with smart defaults"""
    print("\n⚡ Quick Setup Mode\n")
    
    # Auto-detect project
    project_root = os.getcwd()
    project_name = os.path.basename(project_root) or "Project"
    
    # Detect project type
    files = os.listdir(project_root)
    
    # Smart detection
    blacklist_patterns = ['.git/', '__pycache__', '*.pyc']
    
    if 'package.json' in files:
        project_type = "Node.js"
        blacklist_patterns.extend(['node_modules/', 'dist/', 'build/', '*.log'])
    elif 'requirements.txt' in files or 'setup.py' in files:
        project_type = "Python" 
        blacklist_patterns.extend(['venv/', 'env/', '.env/', '*.egg-info/', '.pytest_cache/'])
    elif 'go.mod' in files:
        project_type = "Go"
        blacklist_patterns.extend(['vendor/', 'bin/'])
    else:
        project_type = "Generic"
    
    print(f"✅ Detected: {project_type} project")
    print(f"📁 Root: {project_root}")
    print(f"🚫 Auto-excluding: {', '.join(blacklist_patterns[:5])}...")
    
    # Create config
    config = {
        'wizard_version': '2.0',
        'has_single_root': True,
        'system_type': 'local',
        'project_root': project_root,
        'directories': [{
            'name': project_name,
            'directory': project_root,
            'is_remote': False
        }],
        'blacklist': {
            project_root: blacklist_patterns
        },
        'background': f"This is a {project_type} project located at {project_root}.",
        'rules': 'Follow language-specific best practices and conventions.',
        'current_goal': 'Assist with development tasks.'
    }
    
    # Save config
    with open('gpt_helper_config.json', 'w') as f:
        json.dump(config, f, indent=4)
    
    print("\n✅ Quick setup complete!")
    print("💡 Run 'python main.py --setup' to customize further\n")
    
    return config


# Update main.py to use consolidated setup
def update_main_setup_function():
    """
    Replace the run_config_setup function in main.py to use consolidated setup
    """
    setup_code = '''
def run_config_setup():
    """Run configuration setup using the consolidated wizard"""
    
    print("\\n🎨 Starting GPT Helper Setup Wizard...")
    print("="*60)
    
    # Check for quick setup option
    if len(sys.argv) > 1 and sys.argv[1] == "--setup-quick":
        from setup.run_consolidated import run_quick_setup
        return run_quick_setup()
    
    # Run the consolidated setup wizard
    print("\\n🚀 Launching improved setup wizard...")
    from setup.run_consolidated import run_consolidated_setup
    config = run_consolidated_setup()
    
    if config:
        print("\\n✅ Setup completed successfully!")
        return config
    else:
        print("\\n❌ Setup cancelled")
        return None
'''
    return setup_code