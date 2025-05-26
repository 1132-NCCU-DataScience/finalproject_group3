class TestingConfig:
    TESTING = True
    DEBUG = True # Often helpful for tests
    # Add other testing-specific configs here, e.g.:
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory DB for tests
    # SECRET_KEY = 'test_secret_key'
    # WTF_CSRF_ENABLED = False # Disable CSRF for testing forms if you use Flask-WTF 