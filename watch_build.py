from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess, time, sys, os

BUILD_CMD = [
    sys.executable, "make_fragments_strict.py", "build",
    "--template", "index.template.html",
    "--out", "index.html",
    "--no-backup"
]

class H(FileSystemEventHandler):
    def on_modified(self, e):
        if e.is_directory:
            return
        if not e.src_path.endswith(".html"):
            return

        # run from repo root (where this script is)
        cwd = os.path.dirname(os.path.abspath(__file__))
        print(f"[watch] changed: {e.src_path} -> rebuilding index.html")
        subprocess.run(BUILD_CMD, cwd=cwd)

    # Some editors trigger "created/moved" instead of modified
    def on_created(self, e):
        self.on_modified(e)

    def on_moved(self, e):
        self.on_modified(e)

o = Observer()
o.schedule(H(), "fragments", recursive=True)
o.start()
print("Watching fragments/... auto-building index.html on save")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    o.stop()
o.join()