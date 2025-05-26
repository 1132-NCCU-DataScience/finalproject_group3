from flask import Flask
from config import load_config # Import the loader

app = Flask(__name__, template_folder='templates', static_folder='static')

load_config(app) # Load configuration

# Import routes after app is initialized and configured
from .api import routes
