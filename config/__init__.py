import os

CONFIG_NAME_MAPPER = {
    'development': 'config.development.DevelopmentConfig',
    'testing': 'config.testing.TestingConfig',
    'production': 'config.production.ProductionConfig',
    'default': 'config.development.DevelopmentConfig' # Default to development if FLASK_ENV is not set
}

def load_config(app):
    config_name = os.getenv('FLASK_ENV', 'default')
    config_path = CONFIG_NAME_MAPPER.get(config_name.lower(), CONFIG_NAME_MAPPER['default'])
    app.config.from_object(config_path)
    print(f"Loaded config: {config_path}") # For debugging
