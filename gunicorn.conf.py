import multiprocessing

# Bind
bind = "0.0.0.0:8000"

# Workers: fórmula recomendada para apps CPU-bound (forecast usa numpy/pandas)
# Usar 2-4 workers fijos en vez de la fórmula 2*CPU+1 para evitar OOM con Prophet/SARIMA
workers = int(multiprocessing.cpu_count() * 1.5)
worker_class = "sync"
threads = 2

# Timeouts — forecast puede tardar varios segundos con Prophet
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"   # stdout → capturado por systemd/supervisor
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sµs'

# Proceso
preload_app = True   # carga el modelo Django una vez, lo forkan los workers
max_requests = 500   # reinicia worker cada N requests (evita memory leaks)
max_requests_jitter = 50
