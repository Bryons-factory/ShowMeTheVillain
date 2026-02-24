"""
routes/ package initialization
Exports all route modules for easy importing
"""

from . import phishing
from . import analytics

__all__ = ["phishing", "analytics"]
