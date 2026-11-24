from __future__ import annotations
import json, threading, tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from packdoctor import PackDoctor

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bedrock Pack Doctor")
        self.geometry("920x620")
        self.minsize(760, 500)
        self._build()
    def _build(self):
        top=ttk.Frame(self,padding=12); top.pack(fill="x")
        ttk.Label(top,text="Bedrock Pack Doctor",font=("Segoe UI",16,"bold")).pack(anchor="w")
        ttk.Label(top,text="Read-only validation for .mcpack, .mcaddon and extracted pack folders.").pack(anchor="w",pady=(2,8))
        row=ttk.Frame(top); row.pack(fill="x")
        self.path=tk.StringVar()
        ttk.Entry(row,textvariable=self.path).pack(side="left",fill="x",expand=True)
        ttk.Button(row,text="Choose",command=self.choose).pack(side="left",padx=6)
        self.scan_btn=ttk.Button(row,text="Scan",command=self.scan); self.scan_btn.pack(side="left")
        self.status=tk.StringVar(value="Ready")
        ttk.Label(top,textvariable=self.status).pack(anchor="w",pady=(8,0))
        body=ttk.Frame(self,padding=(12,0,12,12)); body.pack(fill="both",expand=True)
        cols=("level","path","message")
        self.tree=ttk.Treeview(body,columns=cols,show="headings")
        for c,w in zip(cols,(90,300,480)):
            self.tree.heading(c,text=c.title()); self.tree.column(c,width=w,anchor="w")
        self.tree.pack(side="left",fill="both",expand=True)
        sb=ttk.Scrollbar(body,orient="vertical",command=self.tree.yview); sb.pack(side="right",fill="y"); self.tree.configure(yscrollcommand=sb.set)
        bottom=ttk.Frame(self,padding=12); bottom.pack(fill="x")
        self.summary=tk.StringVar(value="No scan yet.")
        ttk.Label(bottom,textvariable=self.summary).pack(side="left")
        ttk.Button(bottom,text="Export JSON",command=self.export).pack(side="right")
    def choose(self):
        p=filedialog.askopenfilename(filetypes=[("Bedrock packs","*.mcpack *.mcaddon *.zip"),("All files","*.*")])
        if p: self.path.set(p)
        else:
            p=filedialog.askdirectory(title="Choose extracted pack folder")
            if p:self.path.set(p)
    def scan(self):
        target=Path(self.path.get())
        if not target.exists(): messagebox.showerror("Scan","Choose a valid file or folder."); return
        self.scan_btn.configure(state="disabled"); self.status.set("Scanning...")
        def work():
            d=PackDoctor()
            try: d.scan(target); result=d.report(); err=None
            except Exception as e: result=None; err=str(e)
            self.after(0,lambda:self.finish(result,err))
        threading.Thread(target=work,daemon=True).start()
    def finish(self,result,err):
        self.scan_btn.configure(state="normal")
        if err: self.status.set("Scan failed"); messagebox.showerror("Scan failed",err); return
        for i in self.tree.get_children(): self.tree.delete(i)
        for f in result["findings"]: self.tree.insert("", "end", values=(f["level"].upper(),f["path"],f["message"]))
        s=result["summary"]; self.summary.set(f'{s["error"]} error(s) • {s["warning"]} warning(s) • {s["info"]} info')
        self.last=result; self.status.set("Scan complete")
    def export(self):
        if not hasattr(self,"last"): messagebox.showinfo("Export","Run a scan first."); return
        p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")])
        if p:
            Path(p).write_text(json.dumps(self.last,indent=2),encoding="utf-8"); self.status.set(f"Saved {p}")

if __name__=="__main__": App().mainloop()
