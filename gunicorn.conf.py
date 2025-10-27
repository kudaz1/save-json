import os

port = os.environ.get("PORT", "8080")
bind = f"0.0.0.0:{port}"
workers = 2
threads = 4
timeout = 120
keepalive = 5
worker_class = "gthread"

