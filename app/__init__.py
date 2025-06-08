from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'  # Change this in a real application!
# Assuming the app is run from the project root directory
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output' # For later use with LaTeX files

# Ensure the upload and output folders exist
import os
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

from app import routes
