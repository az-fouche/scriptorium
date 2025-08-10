"""
Library Explorer Webapp Package

A Flask-based webapp for exploring the indexed library and getting book recommendations.
"""

__version__ = '1.0.0'
__author__ = 'Library Explorer Team'

# Import main components for easy access
from .app_refactored import create_app, app

__all__ = ['create_app', 'app']
