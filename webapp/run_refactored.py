#!/usr/bin/env python3
"""
Run script for the refactored Library Explorer Webapp
"""

import os
import sys

# Add the parent directory to the path so we can import from webapp
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from webapp import create_app

def main():
    """Main entry point"""
    # Create the application
    app = create_app()
    
    # Run the application
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT']
    )

if __name__ == '__main__':
    main()
