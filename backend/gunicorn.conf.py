import os

# One worker: all requests share the in-process _detector_cache.
# Multiple workers each hold their own copy — no shared memory between processes.
workers = 1

# Raise the timeout well above the worst-case first-request training time.
# Default is 30 s; OCSVM + pre-warm on a cold Render container can take ~60 s.
timeout = 120

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
