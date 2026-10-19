"""
gui.py
小分表处理工具 —— 图形界面（批量处理 / 单文件处理 两个选项卡）
"""

import os
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import processor
import subprocess


# ==================== 公共基类：考试信息 + 日志 + 状态栏 ====================

class BaseTab(ttk.Frame):
    """共享"考试信息"输入区、日志区和状态栏的基类"""

    def __init__(self, parent):
        super().__init__(parent)
        self.exam_var = tk.StringVar()
        self.class_var = tk.StringVar()

    # ---------- 状态栏 ----------
    def set_status(self, msg):
        """更新主窗口底部状态栏（由 App 提供 status_var）"""
        top = self.winfo_toplevel()
        if hasattr(top, "status_var"):
            top.status_var.set(msg)

    # ---------- 考试信息 ----------
    def _build_exam_info(self, parent):
        info = ttk.LabelFrame(parent, text="考试信息（可留空）")
        ttk.Label(info, text="考试名称：").grid(row=0, column=0, sticky="w",
                                               padx=8, pady=6)
        ttk.Entry(info, textvariable=self.exam_var).grid(row=0, column=1,
                                                         sticky="ew", padx=4)
        ttk.Label(info, text="班级（纯数字）：").grid(row=1, column=0, sticky="w",
                                                   padx=8, pady=6)
        ttk.Entry(info, textvariable=self.class_var).grid(row=1, column=1,
                                                          sticky="ew", padx=4)
        info.columnconfigure(1, weight=1)
        return info

    # ---------- 日志 ----------
    def _build_log(self, parent):
        log_frame = ttk.LabelFrame(parent, text="运行日志")
        self.log_text = tk.Text(log_frame, wrap="word", height=14,
                                state="disabled", font=("Consolas", 10))
        self.log_text.pack(side="left", fill="both", expand=True,
                           padx=(6, 0), pady=6)
        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        sb.pack(side="right", fill="y", pady=6)
        self.log_text.config(yscrollcommand=sb.set)
        return log_frame

    def log(self, msg):
        self.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", str(msg) + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    # ---------- 班级校验 ----------
    def get_class(self):
        cls = self.class_var.get().strip()
        if cls and not cls.isdigit():
            messagebox.showerror("错误", "班级必须是纯数字")
            return None
        return cls


# ==================== 选项卡 1：批量处理 ====================

class BatchTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent)
        self.input_var = tk.StringVar(value=os.path.abspath("resources"))
        self.output_var = tk.StringVar(value=os.path.abspath("production"))
        self.auto_open_var = tk.BooleanVar(value=True)
        self.start_btn = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # 文件夹设置
        top = ttk.LabelFrame(self, text="文件夹设置")
        top.pack(fill="x", **pad)
        ttk.Label(top, text="输入文件夹：").grid(row=0, column=0,
                                                sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.input_var).grid(row=0, column=1,
                                                         sticky="ew", padx=4)
        ttk.Button(top, text="选择...",
                   command=self.choose_input).grid(row=0, column=2, padx=6)

        ttk.Label(top, text="输出文件夹：").grid(row=1, column=0,
                                                sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.output_var).grid(row=1, column=1,
                                                          sticky="ew", padx=4)
        ttk.Button(top, text="选择...",
                   command=self.choose_output).grid(row=1, column=2, padx=6)
        top.columnconfigure(1, weight=1)

        # 考试信息
        info = self._build_exam_info(self)
        info.pack(fill="x", **pad)

        # 选项与按钮
        mid = ttk.Frame(self)
        mid.pack(fill="x", **pad)
        ttk.Checkbutton(mid, text="处理完成后自动打开输出文件夹",
                        variable=self.auto_open_var).pack(side="left", padx=6)
        self.start_btn = ttk.Button(mid, text="开始批量处理",
                                    command=self.on_start)
        self.start_btn.pack(side="right", padx=6)

        # 日志
        log_frame = self._build_log(self)
        log_frame.pack(fill="both", expand=True, **pad)

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

    def on_start(self):
        in_dir = self.input_var.get().strip()
        out_dir = self.output_var.get().strip()

        if not in_dir or not os.path.isdir(in_dir):
            messagebox.showerror("错误", f"输入文件夹不存在：\n{in_dir}")
            return
        if not out_dir:
            messagebox.showerror("错误", "请填写输出文件夹")
            return

        cls = self.get_class()
        if cls is None:
            return

        self.clear_log()
        self.start_btn.config(state="disabled")
        self.set_status("批量处理中...")

        t = threading.Thread(target=self._run,
                             args=(in_dir, out_dir, cls), daemon=True)
        t.start()

    def _run(self, in_dir, out_dir, cls):
        try:
            exam_name = self.exam_var.get().strip()
            self.log(f"输入：{in_dir}")
            self.log(f"输出：{out_dir}")
            if exam_name or cls:
                self.log(f"考试名称：{exam_name or '（空）'}，"
                         f"班级：{cls or '（空）'}")

            ok, fail = processor.batch_process(
                in_dir, out_dir,
                log=self.log,
                exam_name=exam_name,
                class_num=cls,
            )

            if self.auto_open_var.get() and os.path.isdir(out_dir):
                try:
                    os.startfile(os.path.abspath(out_dir))
                except Exception:
                    pass

            self.after(0, lambda: self.set_status(
                f"完成：成功 {ok}，失败 {fail}"))
        except Exception as e:
            self.log(f"发生异常：{e}")
            self.log(traceback.format_exc())
            self.after(0, lambda: self.set_status("出错"))
        finally:
            self.after(0, lambda: self.start_btn.config(state="normal"))


# ==================== 选项卡 2：单文件处理 ====================

class SingleTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent)
        self.input_var = tk.StringVar()
        self.auto_open_var = tk.BooleanVar(value=True)   # 新增
        self.start_btn = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # 文件选择
        top = ttk.LabelFrame(self, text="文件选择")
        top.pack(fill="x", **pad)
        ttk.Label(top, text="输入文件：").grid(row=0, column=0,
                                              sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.input_var).grid(row=0, column=1,
                                                         sticky="ew", padx=4)
        ttk.Button(top, text="选择文件...",
                   command=self.choose_file).grid(row=0, column=2, padx=6)
        top.columnconfigure(1, weight=1)

        # 考试信息
        info = self._build_exam_info(self)
        info.pack(fill="x", **pad)

        # 选项与按钮
        mid = ttk.Frame(self)
        mid.pack(fill="x", **pad)
        ttk.Checkbutton(mid, text="处理完成后自动打开保存位置",
                        variable=self.auto_open_var).pack(side="left", padx=6)
        self.start_btn = ttk.Button(mid, text="开始处理并保存...",
                                    command=self.on_start)
        self.start_btn.pack(side="right", padx=6)

        # 日志
        log_frame = self._build_log(self)
        log_frame.pack(fill="both", expand=True, **pad)

    # ---------- 回调 ----------
    def choose_file(self):
        init = self.input_var.get()
        init_dir = os.path.dirname(init) if init else os.getcwd()
        f = filedialog.askopenfilename(
            title="选择要处理的 Excel 文件",
            initialdir=init_dir,
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if f:
            self.input_var.set(f)

    def on_start(self):
        input_file = self.input_var.get().strip()
        if not input_file or not os.path.isfile(input_file):
            messagebox.showerror("错误", f"输入文件不存在：\n{input_file}")
            return

        cls = self.get_class()
        if cls is None:
            return

        # 弹出保存对话框（主线程）
        in_dir = os.path.dirname(input_file) or os.getcwd()
        name, _ = os.path.splitext(os.path.basename(input_file))
        default_name = f"{name}_处理后.xlsx"

        output_file = filedialog.asksaveasfilename(
            title="选择保存位置",
            initialdir=in_dir,
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
        )
        if not output_file:
            return  # 用户取消

        if not output_file.lower().endswith(".xlsx"):
            output_file = os.path.splitext(output_file)[0] + ".xlsx"

        exam_name = self.exam_var.get().strip()
        self.clear_log()
        self.start_btn.config(state="disabled")
        self.set_status("处理中...")

        t = threading.Thread(
            target=self._run,
            args=(input_file, output_file, exam_name, cls),
            daemon=True,
        )
        t.start()

    def _open_in_explorer(self, file_path):
        """
        用资源管理器打开文件所在目录并选中该文件。
        失败时退化为只打开所在文件夹。
        """
        try:
            norm = os.path.normpath(file_path)
            subprocess.Popen(["explorer", f"/select,{norm}"])
        except Exception:
            try:
                os.startfile(os.path.dirname(file_path))
            except Exception as e:
                self.log(f"  ⚠️ 无法打开保存位置：{e}")

    def _run(self, input_file, output_file, exam_name, cls):
        try:
            self.log(f"输入：{input_file}")
            self.log(f"输出：{output_file}")
            if exam_name or cls:
                self.log(f"考试名称：{exam_name or '（空）'}，"
                         f"班级：{cls or '（空）'}")

            processor.process_one(
                input_file, output_file,
                log=self.log,
                exam_name=exam_name,
                class_num=cls,
            )
            self.log("\n✅ 处理完成。")
            self.after(0, lambda: self.set_status("完成"))

            # 处理完成后自动打开保存位置
            if self.auto_open_var.get():
                self._open_in_explorer(output_file)

            self.after(0, lambda: messagebox.showinfo(
                "完成", f"文件已保存到：\n{output_file}"))

        except Exception as e:
            self.log(f"发生异常：{e}")
            self.log(traceback.format_exc())
            self.after(0, lambda: self.set_status("出错"))
            self.after(0, lambda: messagebox.showerror(
                "处理失败", str(e)))

        finally:
            self.after(0, lambda: self.start_btn.config(state="normal"))


# ==================== 选项卡 3：班级对比处理 ====================

class ClassCompareTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent)
        self.input_var = tk.StringVar()
        self.auto_open_var = tk.BooleanVar(value=True)
        self.start_btn = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # 文件选择
        top = ttk.LabelFrame(self, text="文件选择")
        top.pack(fill="x", **pad)
        ttk.Label(top, text="输入文件：").grid(row=0, column=0,
                                              sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.input_var).grid(row=0, column=1,
                                                         sticky="ew", padx=4)
        ttk.Button(top, text="选择文件...",
                   command=self.choose_file).grid(row=0, column=2, padx=6)
        top.columnconfigure(1, weight=1)

        # 选项与按钮
        mid = ttk.Frame(self)
        mid.pack(fill="x", **pad)
        ttk.Checkbutton(mid, text="处理完成后自动打开保存位置",
                        variable=self.auto_open_var).pack(side="left", padx=6)
        self.start_btn = ttk.Button(mid, text="开始处理并保存...",
                                    command=self.on_start)
        self.start_btn.pack(side="right", padx=6)

        # 日志
        log_frame = self._build_log(self)
        log_frame.pack(fill="both", expand=True, **pad)

    def choose_file(self):
        init = self.input_var.get()
        init_dir = os.path.dirname(init) if init else os.getcwd()
        f = filedialog.askopenfilename(
            title="选择班级对比表",
            initialdir=init_dir,
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if f:
            self.input_var.set(f)

    def _open_in_explorer(self, file_path):
        try:
            norm = os.path.normpath(file_path)
            subprocess.Popen(["explorer", f"/select,{norm}"])
        except Exception:
            try:
                os.startfile(os.path.dirname(file_path))
            except Exception as e:
                self.log(f"  ⚠️ 无法打开保存位置：{e}")

    def on_start(self):
        input_file = self.input_var.get().strip()
        if not input_file or not os.path.isfile(input_file):
            messagebox.showerror("错误", f"输入文件不存在：\n{input_file}")
            return

        in_dir = os.path.dirname(input_file) or os.getcwd()
        name, _ = os.path.splitext(os.path.basename(input_file))
        default_name = f"{name}_处理后.xlsx"

        output_file = filedialog.asksaveasfilename(
            title="选择保存位置",
            initialdir=in_dir,
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
        )
        if not output_file:
            return

        if not output_file.lower().endswith(".xlsx"):
            output_file = os.path.splitext(output_file)[0] + ".xlsx"

        self.clear_log()
        self.start_btn.config(state="disabled")
        self.set_status("处理中...")

        t = threading.Thread(target=self._run,
                             args=(input_file, output_file), daemon=True)
        t.start()

    def _run(self, input_file, output_file):
        try:
            self.log(f"输入：{input_file}")
            self.log(f"输出：{output_file}")

            processor.process_class_compare(input_file, output_file, log=self.log)

            self.log("\n✅ 处理完成。")
            self.after(0, lambda: self.set_status("完成"))

            if self.auto_open_var.get():
                self._open_in_explorer(output_file)

            self.after(0, lambda: messagebox.showinfo(
                "完成", f"文件已保存到：\n{output_file}"))
        except Exception as e:
            self.log(f"发生异常：{e}")
            self.log(traceback.format_exc())
            self.after(0, lambda: self.set_status("出错"))
            self.after(0, lambda: messagebox.showerror(
                "处理失败", str(e)))
        finally:
            self.after(0, lambda: self.start_btn.config(state="normal"))


# ==================== 主窗口 ====================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("小分表处理工具")
        self.geometry("820x680")
        self.minsize(740, 600)

        # ---- 选项卡 ----
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.single_tab = SingleTab(notebook)
        self.batch_tab = BatchTab(notebook)
        self.class_compare_tab = ClassCompareTab(notebook)

        notebook.add(self.single_tab, text="   小分表单文件处理   ")
        notebook.add(self.batch_tab, text="   小分表批量处理   ")
        notebook.add(self.class_compare_tab, text="   班级对比处理   ")

        # ---- 状态栏（主窗口底部，扁平） ----
        status_bar = ttk.Frame(self)
        status_bar.pack(fill="x", side="bottom", padx=10, pady=(6, 6))

        ttk.Separator(status_bar, orient="horizontal").pack(fill="x")

        self.status_var = tk.StringVar(value="就绪")
        status = ttk.Label(status_bar, textvariable=self.status_var,
                           anchor="w", relief="flat", borderwidth=0,
                           padding=(4, 4))
        status.pack(fill="x")


def main():
    App().mainloop()
