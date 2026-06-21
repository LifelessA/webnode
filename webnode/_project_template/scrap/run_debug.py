import signal, sys, traceback, threading, os

def crash_handler(signum, frame):
    with open('crash_signal.log', 'w') as f:
        f.write(f"Signal received: {signum}\n")
        traceback.print_stack(frame, file=f)
    print(f"SIGNAL {signum} received!", flush=True)
    traceback.print_stack(frame)
    sys.exit(1)

# Catch common termination signals
signal.signal(signal.SIGTERM, crash_handler)
signal.signal(signal.SIGINT, crash_handler)
signal.signal(signal.SIGBREAK, crash_handler)

# Monitor thread crashes
original_init = threading.Thread.__init__
def patched_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    original_run = self.run
    def wrapped_run():
        try:
            original_run()
        except Exception as e:
            print(f"THREAD CRASH: {e}", flush=True)
            traceback.print_exc()
            with open('crash_thread.log', 'w') as f:
                f.write(f"Thread crash: {e}\n")
                traceback.print_exc(file=f)
    self.run = wrapped_run
threading.Thread.__init__ = patched_init

print(f"PID: {os.getpid()}", flush=True)
print("Starting main.py with crash monitoring...", flush=True)

try:
    with open('main.py', 'r', encoding='utf-8') as f:
        code = f.read()
    exec(compile(code, 'main.py', 'exec'))
except SystemExit as e:
    print(f"SystemExit: {e}", flush=True)
except Exception as e:
    print(f"EXCEPTION: {e}", flush=True)
    traceback.print_exc()
finally:
    print("Server process ending!", flush=True)
