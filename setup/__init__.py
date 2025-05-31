"""
Setup package for GPT Helper - Consolidated version
"""

# Import main setup functionality
from .wizard_base import SetupWizard, WizardStep
from .overall_setup import OverallSetupStep
from .directory_config import DirectoryConfigStep  
from .blacklist_setup import BlacklistSetupStep
from .content_setup import ContentSetupStep

def run_setup():
    """Run the consolidated setup wizard"""
    # Create wizard instance
    wizard = SetupWizard()
    
    # Add steps with improved flow
    wizard.add_step(OverallSetupStep(wizard))
    wizard.add_step(DirectoryConfigStep(wizard))
    wizard.add_step(BlacklistSetupStep(wizard))
    wizard.add_step(ContentSetupStep(wizard))
    
    # Run wizard
    if wizard.run():
        return wizard.config
    else:
        return None

# Export main functionality
__all__ = [
    'run_setup',
    'SetupWizard',
    'WizardStep'
]
