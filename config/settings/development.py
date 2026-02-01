"""
This file is a shim to prevent crashes if DJANGO_SETTINGS_MODULE is set to
'config.settings.development' in the deployment environment.
It imports everything from base (production settings).
"""
from .base import *
