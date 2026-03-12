from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess, time, os

class H(FileSystemEventHandler):
    def on_modified(self, e):
        if e.is_directory: return
        if e.src_path.endswith(".html"):
            subprocess.call(["python", "make_fragments_strict.py", "build",
                             "--template", "index.template.html",
                             "--out", "index.html",
                             "--no-backup"])

o = Observer()
o.schedule(H(), "fragments", recursive=True)
o.start()
print("Watching fragments/... auto-building index.html on save")
try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    o.stop()
o.join()