# This file is for pytest fixtures, hooks, etc.
# For example, you might define a fixture for your Flask app context:

# import pytest
# from app import app as flask_app # Assuming your Flask app instance is named 'app' in app/__init__.py

# @pytest.fixture(scope='session')
# def app():
#     """Session-wide test Flask app."""
#     # Setup: ensure app is configured for testing
#     flask_app.config.update({
#         "TESTING": True,
#         # Add other test-specific configurations here, e.g.,
#         # "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
#         # "WTF_CSRF_ENABLED": False,
#     })
#     return flask_app

# @pytest.fixture()
# def client(app):
#     """A test client for the app."""
#     return app.test_client()

# @pytest.fixture()
# def runner(app):
#     """A test runner for the app's Click commands."""
#     return app.test_cli_runner()

# -*- coding: utf-8 -*-
import pytest
import os

# To ensure the app loads the testing config, we can try to set FLASK_ENV.
# However, the app is initialized globally in app/__init__.py and loads config immediately.
# A common approach is to get the global app instance and reconfigure it for tests.

from app import app as flask_app_instance

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask app configured for testing."""
    
    # Ensure the app uses the testing configuration
    # This might override parts of what load_config did if FLASK_ENV wasn't 'testing' initially
    flask_app_instance.config.from_object('config.testing.TestingConfig')
    
    # Explicitly set common testing flags, ensuring they are active
    flask_app_instance.config["TESTING"] = True
    flask_app_instance.config["DEBUG"] = True # Often useful for debugging tests
    flask_app_instance.config["WTF_CSRF_ENABLED"] = False # Example: if using Flask-WTF
    
    # If your app has a database, you might want to set up a test database here
    # Example: flask_app_instance.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    # Create a fresh app context for the test session
    # Not strictly necessary if just using test_client, but good practice for some tests
    # with flask_app_instance.app_context():
    #     # yield flask_app_instance # if you need to do something within app_context
    #     pass # App context not explicitly yielded here, client fixture will handle it
        
    return flask_app_instance

@pytest.fixture()
def client(app):
    """A test client for the app."""
    # The test client pushes an application context when used with `with client:` or when making requests.
    return app.test_client()

# If you have Click commands in your Flask app (e.g., via app.cli)
# @pytest.fixture()
# def runner(app):
#     """A test runner for the app's Click commands."""
#     return app.test_cli_runner() 