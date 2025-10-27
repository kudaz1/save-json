import os

bind = "0.0.0.0:" + str(os.environ.get("PORT", 8080))
workers = 2
threads = 4
timeout = 120
keepalive = 5

