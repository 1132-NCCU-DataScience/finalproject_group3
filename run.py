#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
from app import app # Import the app instance from app/__init__.py

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Starlink Taipei Flask App')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    # Add a debug argument, defaulting to False for a run.py script
    # For development, one might run this with --debug
    parser.add_argument('--debug', action='store_true', help='Enable Flask debug mode')

    args = parser.parse_args()

    # Ensure output directory exists (though app factory in __init__ might also do this)
    # The static_folder in app/__init__.py is '../output'. 
    # So from the perspective of app/__init__.py, it expects 'output' to be in the project root.
    # Let's ensure it exists here.
    output_dir = os.path.join(os.path.dirname(__file__), 'output') 
    # Correction: The app static_folder is app/output now, as configured in app/__init__.py as static_folder='../output' relative to app directory. 
    # And we moved the original output to app/output.
    # So the check for output_dir should be for app/output.
    app_output_dir = os.path.join(os.path.dirname(__file__), 'app', 'output')
    if not os.path.exists(app_output_dir):
        os.makedirs(app_output_dir)
        print(f"Created directory: {app_output_dir}")

    # The original app.py had a startup routine for analysis_status.
    # This logic should ideally be within the app's initialization or a startup hook,
    # but for now, to maintain parity, we can replicate it here if necessary.
    # However, the `analysis_status` is defined in `app.api.routes`.
    # Directly modifying it here would be a bit messy.
    # For now, let's assume the default state in routes.py is sufficient on startup.

    app.run(debug=args.debug, host=args.host, port=args.port) 