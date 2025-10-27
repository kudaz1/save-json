import os
import sys

# Railway runs this to start the app
port = os.environ.get('PORT', '8080')

os.system(f'gunicorn app:app --bind 0.0.0.0:{port} --workers 4')

