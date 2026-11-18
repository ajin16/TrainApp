"""
Production Gunicorn Configuration for IRCTC TrainApp
"""
import os
import multiprocessing

# Network binding
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Worker processes: sensible default for web containers, configurable via WEB_CONCURRENCY
workers = int(os.getenv('WEB_CONCURRENCY', max(2, min(4, multiprocessing.cpu_count()))))
threads = int(os.getenv('GUNICORN_THREADS', 2))
worker_class = 'gthread'

# Timeouts & Keep-Alive
timeout = int(os.getenv('GUNICORN_TIMEOUT', 120))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', 5))
graceful_timeout = 30

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('GUNICORN_LOGLEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(D)s µs)'

# Server Mechanics
preload_app = False
capture_output = True
