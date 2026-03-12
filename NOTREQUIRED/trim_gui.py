import tkinter as tk
from tkinter import filedialog, messagebox
from pydub import AudioSegment
def trim():
    path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav")])
    if not path: return
    try:
        end = float(e.get()) * 1000
        audio = AudioSegment.from_file(path)
        audio[75000:end].export("trimmed.mp3", format="mp3")
        messagebox.showinfo("Done", "Saved as trimmed.mp3")
    except Exception as err: messagebox.showerror("Error", str(err))
root = tk.Tk(); root.title("Trimmer")
tk.Label(root, text="End Time (sec):").pack()
e = tk.Entry(root); e.insert(0, "120"); e.pack()
tk.Button(root, text="Select & Trim", command=trim).pack()
root.mainloop()
