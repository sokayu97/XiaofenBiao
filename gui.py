"""
gui.py
小分表批量处理工具 —— 图形界面
"""

import os
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import processor


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("小分表批量处理工具")
        self.geometry("760x540")
        self.minsize(680, 460)

        self.input_var = tk.StringVar(value=os.path.abspath("resources"))
        self.output_var = tk.StringVar(value=os.path.abspath("production"))
        self.auto_open_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # 顶部：文件夹选择
        top = ttk.LabelFrame(self, text="文件夹设置")
        top.pack(fill="x", **pad)

        ttk.Label(top, text="输入文件夹：").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.input_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(top, text="选择...", command=self.choose_input).grid(row=0, column=2, padx=6)

        ttk.Label(top, text="输出文件夹：").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(top, text="选择...", command=self.choose_output).grid(row=1, column=2, padx=6)

        top.columnconfigure(1, weight=1)

        # 中部：选项与按钮
        mid = ttk.Frame(self)
        mid.pack(fill="x", **pad)

        ttk.Checkbutton(mid, text="处理完成后自动打开输出文件夹",
                        variable=self.auto_open_var).pack(side="left", padx=6)

        self.start_btn = ttk.Button(mid, text="开始处理", command=self.on_start)
        self.start_btn.pack(side="right", padx=6)

        # 日志区
        log_frame = ttk.LabelFrame(self, text="运行日志")
        log_frame.pack(fill="both", expand=True, **pad)

        self.log_text = tk.Text(log_frame, wrap="word", height=18,
                                state="disabled", font=("Consolas", 10))
        self.log_text.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)

        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        sb.pack(side="right", fill="y", pady=6)
        self.log_text.config(yscrollcommand=sb.set)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w", relief="sunken")
        status.pack(fill="x", side="bottom")

    # ---------- 回调 ----------
    def choose_input(self):
        d = filedialog.askdirectory(title="选择输入文件夹",
                                    initialdir=self.input_var.get() or os.getcwd())
        if d:
            self.input_var.set(d)

    def choose_output(self):
        d = filedialog.askdirectory(title="选择输出文件夹",
                                    initialdir=self.output_var.get() or os.getcwd())
        if d:
            self.output_var.set(d)

    def log(self, msg):
        """线程安全地写日志"""
        self.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", str(msg) + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def on_start(self):
        in_dir = self.input_var.get().strip()
        out_dir = self.output_var.get().strip()

        if not in_dir or not os.path.isdir(in_dir):
            messagebox.showerror("错误", f"输入文件夹不存在：\n{in_dir}")
            return
        if not out_dir:
            messagebox.showerror("错误", "请填写输出文件夹")
            return

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

        self.start_btn.config(state="disabled")
        self.status_var.set("处理中...")

        t = threading.Thread(target=self._run, args=(in_dir, out_dir), daemon=True)
        t.start()

    def _run(self, in_dir, out_dir):
        try:
            self.log(f"输入：{in_dir}")
            self.log(f"输出：{out_dir}")
            ok, fail = processor.batch_process(in_dir, out_dir, log=self.log)

            if self.auto_open_var.get() and os.path.isdir(out_dir):
                try:
                    os.startfile(os.path.abspath(out_dir))
                except Exception:
                    pass

            self.after(0, lambda: self.status_var.set(f"完成：成功 {ok}，失败 {fail}"))
        except Exception as e:
            self.log(f"发生异常：{e}")
            self.log(traceback.format_exc())
            self.after(0, lambda: self.status_var.set("出错"))
        finally:
            self.after(0, lambda: self.start_btn.config(state="normal"))


def main():
    App().mainloop()
