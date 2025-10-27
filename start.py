import os

# Railway runs this to start the app
port = os.environ.get('PORT', '5000')

print(f"Starting on port: {port}")
print(f"PORT env var: {os.environ.get('PORT', 'NOT SET')}")

os.system(f'gunicorn app:app --bind 0.0.0.0:{port} --workers 4')

