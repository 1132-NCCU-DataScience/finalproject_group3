class ProductionConfig:
    DEBUG = False
    # Add other production-specific configs here, e.g.:
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///prod.db'
    # SECRET_KEY = os.environ.get('SECRET_KEY') # 절대 하드코딩하지 마세요!
    # Consider Gunicorn/uWSGI specific settings if needed to be passed via app config 