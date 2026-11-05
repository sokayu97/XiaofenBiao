"""
gui.py
小分表处理工具 —— 图形界面
"""
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
import traceback
import webbrowser
from tkinter import ttk, filedialog, messagebox

import processor
from config import load_configs, default_config, create_default_configs, pick_default_key
from config_editor import ConfigEditor


# ---- 兼容 PyInstaller 的资源路径获取 ----
def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发环境和 PyInstaller 单文件模式"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 单文件模式解压后的临时路径
        base_path = sys._MEIPASS
    else:
        # 正常 Python 运行环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ---- 关于页信息（按需修改） ----
APP_VERSION = "1.3.0"
AUTHOR_NAME = "刘老师1"
AUTHOR_GITHUB = "https://github.com/sokayu97/XiaofenBiao"
DEV_ASSISTANT = "DeepSeek (深度求索)"
# 赞赏码的路径
REWARD_IMAGE = get_resource_path(os.path.join("assets", "reward.png"))

# ---- 状态文件：优先放在脚本/exe 所在目录 ----
def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

STATE_FILE = os.path.join(_app_dir(), "app_state.json")


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ==================== 公共基类 ====================

class BaseTab(ttk.Frame):
    def __init__(self, parent, configs, default_key, config_var):
        super().__init__(parent)
        self._configs = dict(configs)
        self._default_key = default_key
        self.config_var = config_var          # 由 App 共享
        self.grade_var = tk.StringVar()
        self.exam_var = tk.StringVar()
        self.class_var = tk.StringVar()

    def set_status(self, msg):
        top = self.winfo_toplevel()
        if hasattr(top, "status_var"):
            top.status_var.set(msg)

    # ---------- 配置选择器 ----------
    def build_config_selector(self, parent):
        frame = ttk.LabelFrame(parent, text="试卷配置")
        ttk.Label(frame, text="配置：").pack(side="left", padx=8, pady=6)
        self.config_combo = ttk.Combobox(
            frame, textvariable=self.config_var,
            values=list(self._configs.keys()), state="readonly", width=28)
        self.config_combo.pack(side="left", padx=4, pady=6)

        ttk.Label(frame, text="年级：").pack(side="left", padx=(16, 4), pady=6)
        ttk.Entry(frame, textvariable=self.grade_var, width=14).pack(side="left", pady=6)

        if not self.config_var.get() and self._default_key in self._configs:
            self.config_var.set(self._default_key)
        return frame

    def refresh_configs(self, configs):
        self._configs = dict(configs)
        if hasattr(self, "config_combo"):
            self.config_combo["values"] = list(configs.keys())

    def get_config(self):
        key = self.config_var.get()
        return self._configs.get(key) if key else None

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

    def get_class(self):
        cls = self.class_var.get().strip()
        if cls and not cls.isdigit():
            messagebox.showerror("错误", "班级必须是纯数字")
            return None
        return cls

    @staticmethod
    def _open_in_explorer(file_path):
        try:
            norm = os.path.normpath(os.path.abspath(file_path))
            if not os.path.exists(norm):
                folder = os.path.dirname(norm)
                if os.path.isdir(folder):
                    os.startfile(folder)
                return
            subprocess.Popen(f'explorer /select,"{norm}"')
        except Exception:
            try:
                os.startfile(os.path.dirname(norm))
            except Exception:
                pass


# ==================== 选项卡 1：小分表单文件处理 ====================

class SingleTab(BaseTab):
    def __init__(self, parent, configs, default_key, config_var):
        super().__init__(parent, configs, default_key, config_var)
        self.input_var = tk.StringVar()
        self.auto_open_var = tk.BooleanVar(value=True)
        self.start_btn = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        cfg_frame = self.build_config_selector(self)
        cfg_frame.pack(fill="x", **pad)

        top = ttk.LabelFrame(self, text="文件选择")
        top.pack(fill="x", **pad)
        ttk.Label(top, text="输入文件：").grid(row=0, column=0,
                                              sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.input_var).grid(row=0, column=1,
                                                         sticky="ew", padx=4)
        ttk.Button(top, text="选择文件...",
                   command=self.choose_file).grid(row=0, column=2, padx=6)
        top.columnconfigure(1, weight=1)

        info = self._build_exam_info(self)
        info.pack(fill="x", **pad)

        mid = ttk.Frame(self)
        mid.pack(fill="x", **pad)
        ttk.Checkbutton(mid, text="处理完成后自动打开保存位置",
                        variable=self.auto_open_var).pack(side="left", padx=6)
        self.start_btn = ttk.Button(mid, text="开始处理并保存...",
                                    command=self.on_start)
        self.start_btn.pack(side="right", padx=6)

        log_frame = self._build_log(self)
        log_frame.pack(fill="both", expand=True, **pad)

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

        in_dir = os.path.dirname(input_file) or os.getcwd()
        name, _ = os.path.splitext(os.path.basename(input_file))
        output_file = filedialog.asksaveasfilename(
            title="选择保存位置",
            initialdir=in_dir,
            initialfile=f"{name}_处理后.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
        )
        if not output_file:
            return
        if not output_file.lower().endswith(".xlsx"):
            output_file = os.path.splitext(output_file)[0] + ".xlsx"

        exam_name = self.exam_var.get().strip()
        self.clear_log()
        self.start_btn.config(state="disabled")
        self.set_status("处理中...")

        threading.Thread(
            target=self._run,
            args=(input_file, output_file, exam_name, cls),
            daemon=True,
        ).start()

    def _run(self, input_file, output_file, exam_name, cls):
        try:
            grade = self.grade_var.get().strip()
            cfg = self.get_config()
            self.log(f"输入：{input_file}")
            self.log(f"输出：{output_file}")
            if cfg:
                self.log(f"配置：{cfg.name}，年级：{grade or cfg.grade}")
            if exam_name or cls:
                self.log(f"考试名称：{exam_name or '（空）'}，班级：{cls or '（空）'}")

            processor.process_one(
                input_file, output_file,
                log=self.log, exam_name=exam_name, class_num=cls,
                grade=grade, cfg=cfg,
            )
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
            self.after(0, lambda: messagebox.showerror("处理失败", str(e)))
        finally:
            self.after(0, lambda: self.start_btn.config(state="normal"))


# ==================== 选项卡 2：小分表批量处理 ====================

class BatchTab(BaseTab):
    def __init__(self, parent, configs, default_key, config_var):
        super().__init__(parent, configs, default_key, config_var)
        self.input_var = tk.StringVar(value=os.path.abspath("resources"))
        self.output_var = tk.StringVar(value=os.path.abspath("production"))
        self.auto_open_var = tk.BooleanVar(value=True)
        self.start_btn = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        cfg_frame = self.build_config_selector(self)
        cfg_frame.pack(fill="x", **pad)

        top = ttk.LabelFrame(self, text="文件夹设置")
        top.pack(fill="x", **pad)
        ttk.Label(top, text="输入文件夹：").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.input_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(top, text="选择...", command=self.choose_input).grid(row=0, column=2, padx=6)
        ttk.Label(top, text="输出文件夹：").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(top, text="选择...", command=self.choose_output).grid(row=1, column=2, padx=6)
        top.columnconfigure(1, weight=1)

        info = self._build_exam_info(self)
        info.pack(fill="x", **pad)

        mid = ttk.Frame(self)
        mid.pack(fill="x", **pad)
        ttk.Checkbutton(mid, text="处理完成后自动打开输出文件夹",
                        variable=self.auto_open_var).pack(side="left", padx=6)
        self.start_btn = ttk.Button(mid, text="开始批量处理", command=self.on_start)
        self.start_btn.pack(side="right", padx=6)

        log_frame = self._build_log(self)
        log_frame.pack(fill="both", expand=True, **pad)

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
        threading.Thread(target=self._run, args=(in_dir, out_dir, cls),
                         daemon=True).start()

    def _run(self, in_dir, out_dir, cls):
        try:
            exam_name = self.exam_var.get().strip()
            grade = self.grade_var.get().strip()
            cfg = self.get_config()
            self.log(f"输入：{in_dir}")
            self.log(f"输出：{out_dir}")
            if cfg:
                self.log(f"配置：{cfg.name}，年级：{grade or cfg.grade}")
            if exam_name or cls:
                self.log(f"考试名称：{exam_name or '（空）'}，班级：{cls or '（空）'}")

            ok, fail = processor.batch_process(
                in_dir, out_dir, log=self.log,
                exam_name=exam_name, class_num=cls, grade=grade, cfg=cfg,
            )
            if self.auto_open_var.get() and os.path.isdir(out_dir):
                try:
                    os.startfile(os.path.abspath(out_dir))
                except Exception:
                    pass
            self.after(0, lambda: self.set_status(f"完成：成功 {ok}，失败 {fail}"))
        except Exception as e:
            self.log(f"发生异常：{e}")
            self.log(traceback.format_exc())
            self.after(0, lambda: self.set_status("出错"))
        finally:
            self.after(0, lambda: self.start_btn.config(state="normal"))


# ==================== 选项卡 3：班级对比处理 ====================

class ClassCompareTab(BaseTab):
    def __init__(self, parent, configs, default_key, config_var):
        super().__init__(parent, configs, default_key, config_var)
        self.input_var = tk.StringVar()
        self.auto_open_var = tk.BooleanVar(value=True)
        self.start_btn = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        cfg_frame = self.build_config_selector(self)
        cfg_frame.pack(fill="x", **pad)

        top = ttk.LabelFrame(self, text="文件选择")
        top.pack(fill="x", **pad)
        ttk.Label(top, text="输入文件：").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.input_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(top, text="选择文件...", command=self.choose_file).grid(row=0, column=2, padx=6)
        top.columnconfigure(1, weight=1)

        mid = ttk.Frame(self)
        mid.pack(fill="x", **pad)
        ttk.Checkbutton(mid, text="处理完成后自动打开保存位置",
                        variable=self.auto_open_var).pack(side="left", padx=6)
        self.start_btn = ttk.Button(mid, text="开始处理并保存...", command=self.on_start)
        self.start_btn.pack(side="right", padx=6)

        log_frame = self._build_log(self)
        log_frame.pack(fill="both", expand=True, **pad)

    def choose_file(self):
        init = self.input_var.get()
        init_dir = os.path.dirname(init) if init else os.getcwd()
        f = filedialog.askopenfilename(
            title="选择班级对比表", initialdir=init_dir,
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if f:
            self.input_var.set(f)

    def on_start(self):
        input_file = self.input_var.get().strip()
        if not input_file or not os.path.isfile(input_file):
            messagebox.showerror("错误", f"输入文件不存在：\n{input_file}")
            return
        in_dir = os.path.dirname(input_file) or os.getcwd()
        name, _ = os.path.splitext(os.path.basename(input_file))
        output_file = filedialog.asksaveasfilename(
            title="选择保存位置", initialdir=in_dir,
            initialfile=f"{name}_处理后.xlsx", defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx")],
        )
        if not output_file:
            return
        if not output_file.lower().endswith(".xlsx"):
            output_file = os.path.splitext(output_file)[0] + ".xlsx"

        self.clear_log()
        self.start_btn.config(state="disabled")
        self.set_status("处理中...")
        threading.Thread(target=self._run, args=(input_file, output_file),
                         daemon=True).start()

    def _run(self, input_file, output_file):
        try:
            cfg = self.get_config()
            self.log(f"输入：{input_file}")
            self.log(f"输出：{output_file}")
            if cfg:
                self.log(f"配置：{cfg.name}")

            processor.process_class_compare(input_file, output_file,
                                            log=self.log, cfg=cfg)

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
            self.after(0, lambda: messagebox.showerror("处理失败", str(e)))
        finally:
            self.after(0, lambda: self.start_btn.config(state="normal"))


# ==================== 选项卡 4：关于 ====================

class AboutTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        wrapper = ttk.Frame(self)
        wrapper.pack(expand=True, fill="both", padx=40, pady=16)
        center = ttk.Frame(wrapper)
        center.pack(expand=True)

        ttk.Label(center, text="小分表处理工具",
                  font=("Microsoft YaHei", 22, "bold")).pack(pady=(0, 4))
        ttk.Label(center, text=f"版本 {APP_VERSION}",
                  font=("Microsoft YaHei", 10), foreground="gray").pack(pady=(0, 14))
        ttk.Label(center, text="面向中学成绩单的自动化处理工具",
                  font=("Microsoft YaHei", 11)).pack(pady=(0, 18))

        feat = ttk.LabelFrame(center, text="功能")
        feat.pack(fill="x", pady=(0, 12))
        features = [
            ("小分表单文件处理", "选择单个小分表，按试卷配置清洗、标红、汇总零分负分名单"),
            ("小分表批量处理", "对 resources 目录批量执行，输出到 production"),
            ("班级对比处理", "汇总各班客观/主观/总分，生成「处理后」工作表"),
            ("配置管理", "图形界面编辑试卷结构、特殊规则与标题模板"),
        ]
        for name, desc in features:
            row = ttk.Frame(feat)
            row.pack(fill="x", padx=12, pady=3)
            ttk.Label(row, text=name, width=18, anchor="w",
                      font=("Microsoft YaHei", 10, "bold")).pack(side="left")
            ttk.Label(row, text=desc, foreground="#444").pack(side="left", padx=6)

        tips = ttk.LabelFrame(center, text="使用提示")
        tips.pack(fill="x", pady=(0, 12))
        for line in [
            "• 试卷结构、卷面分题号、标题模板均可在「⚙ 管理配置」中调整",
            "• 年级、考试名称、班级可在各选项卡中临时覆盖配置",
            "• 处理结果默认输出到 production 目录，可勾选自动打开保存位置",
            "• 支持 .xlsx 文件；批量模式会跳过以 ~$ 开头的临时文件",
        ]:
            ttk.Label(tips, text=line, foreground="#555").pack(anchor="w", padx=12, pady=2)

        author = ttk.LabelFrame(center, text="关于作者")
        author.pack(fill="x", pady=(0, 12))
        ttk.Label(author, text=f"作者：{AUTHOR_NAME}",
                  font=("Microsoft YaHei", 10, "bold")).pack(pady=(8, 2))

        gh = ttk.Label(author, text=AUTHOR_GITHUB, foreground="#0a66c2",
                       cursor="hand2", font=("Consolas", 10))
        gh.pack(pady=2)
        gh.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_GITHUB))
        gh.bind("<Enter>", lambda e: gh.configure(foreground="#1a7fd4"))
        gh.bind("<Leave>", lambda e: gh.configure(foreground="#0a66c2"))

        ttk.Label(author, text=f"开发助手：{DEV_ASSISTANT}",
                  foreground="gray").pack(pady=(2, 8))

        btns = ttk.Frame(center)
        btns.pack(fill="x", pady=(0, 12))
        row1 = ttk.Frame(btns)
        row1.pack(pady=2)
        ttk.Button(row1, text="打开 resources",
                   command=lambda: self._open_dir("resources")).pack(side="left", padx=4)
        ttk.Button(row1, text="打开 production",
                   command=lambda: self._open_dir("production")).pack(side="left", padx=4)
        ttk.Button(row1, text="打开 configs",
                   command=lambda: self._open_dir("configs")).pack(side="left", padx=4)
        ttk.Button(btns, text="💝 赞赏支持",
                   command=self._show_reward).pack(pady=(8, 0))

        ttk.Label(center, text="基于 Python · pandas · openpyxl · tkinter",
                  font=("Consolas", 9), foreground="gray").pack(pady=(6, 0))

    def _open_dir(self, name):
        path = os.path.abspath(name)
        if not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建目录：\n{path}\n\n{e}")
                return
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开：\n{path}\n\n{e}")

    def _show_reward(self):
        path = REWARD_IMAGE # 这里直接用改好的全局变量
        if not os.path.isfile(path):
            messagebox.showwarning(
                "未找到赞赏码",
                f"未找到图片：\n{path}\n\n"
                f"请确保 assets/reward.png 存在。\n"
                f"如果您是打包用户，请确认打包时包含了 assets 文件夹。"
            )
            return
        try:
            from PIL import Image, ImageTk
            img = Image.open(path)
            img.thumbnail((400, 400), Image.LANCZOS)
            top = tk.Toplevel(self)
            top.title("赞赏支持")
            top.resizable(False, False)
            top.transient(self.winfo_toplevel())
            top.grab_set()
            photo = ImageTk.PhotoImage(img)
            lbl = ttk.Label(top, image=photo)
            lbl.image = photo
            lbl.pack(padx=20, pady=(20, 8))
            ttk.Label(top, text="感谢你的支持！",
                      font=("Microsoft YaHei", 11)).pack(pady=(0, 8))
            ttk.Button(top, text="关闭", command=top.destroy).pack(pady=(0, 16))
            return
        except ImportError:
            pass
        except Exception as e:
            messagebox.showerror("错误", f"无法显示赞赏码：\n{e}")
            return
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片：\n{path}\n\n{e}")


# ==================== 主窗口 ====================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("小分表处理工具")
        self.geometry("1000x860")
        self.minsize(900, 780)

        # ---- 配置加载 ----
        create_default_configs("configs")
        self.configs = load_configs("configs")
        if not self.configs:
            self.configs = {"默认（物理）": default_config()}

        # 状态：优先用上次选中的配置，否则物理
        self._state = load_state()
        saved_key = self._state.get("selected_config")
        initial_key = saved_key if saved_key in self.configs else pick_default_key(self.configs)

        # 三个选项卡共享同一个配置变量
        self.config_var = tk.StringVar(value=initial_key)

        # ---- 1. 状态栏先 pack（保证不被挤压） ----
        status_bar = ttk.Frame(self)
        status_bar.pack(fill="x", side="bottom", padx=10, pady=(4, 6))
        ttk.Separator(status_bar, orient="horizontal").pack(fill="x")
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_bar, textvariable=self.status_var, anchor="w",
                  relief="flat", borderwidth=0,
                  padding=(4, 4)).pack(fill="x")

        # ---- 2. 选项卡 ----
        # 注意这里：把 notebook 变成了 self.notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(6, 0))

        self.single_tab = SingleTab(self.notebook, self.configs, initial_key, self.config_var)
        self.batch_tab = BatchTab(self.notebook, self.configs, initial_key, self.config_var)
        self.class_compare_tab = ClassCompareTab(self.notebook, self.configs, initial_key, self.config_var)
        self.about_tab = AboutTab(self.notebook)

        self.notebook.add(self.single_tab, text="   小分表单文件处理   ")
        self.notebook.add(self.batch_tab, text="   小分表批量处理   ")
        self.notebook.add(self.class_compare_tab, text="   班级对比处理   ")
        self.notebook.add(self.about_tab, text="   关于   ")

        # ---- 3. “管理配置”按钮放到 tab 头同一行右侧 ----
        self._cfg_btn = ttk.Button(self, text="⚙ 管理配置",
                                   command=self._open_config_editor)
        # 注意这里：in_ 后面也换成了 self.notebook
        self._cfg_btn.place(in_=self.notebook, relx=1.0, x=-6, y=4, anchor="ne")

        # ---- 4. 监听配置变化，同步年级 + 持久化 ----
        self.config_var.trace_add("write", self._on_config_global_changed)
        self._on_config_global_changed()   # 初始化一次

        # ---- 5. 首次运行跳转到“关于”页面 ----
        if not self._state.get("first_run_done", False):
            self.notebook.select(self.about_tab)  # 切换到关于页
            self._state["first_run_done"] = True  # 标记已运行过
            save_state(self._state)

    # ---------- 配置变化统一处理 ----------
    def _on_config_global_changed(self, *args):
        key = self.config_var.get()
        cfg = self.configs.get(key)
        if cfg:
            for tab in (self.single_tab, self.batch_tab, self.class_compare_tab):
                tab.grade_var.set(cfg.grade)
            save_state({"selected_config": key})

    # ---------- 打开配置编辑器 ----------
    def _open_config_editor(self):
        ConfigEditor(self, config_dir="configs", on_save=self._reload_configs)

    def _reload_configs(self):
        new = load_configs("configs")
        if not new:
            return
        self.configs = new
        for tab in (self.single_tab, self.batch_tab, self.class_compare_tab):
            tab.refresh_configs(new)
        current = self.config_var.get()
        if current not in new:
            self.config_var.set(pick_default_key(new))
        else:
            # 值未变，但内容可能变了，手动触发一次同步
            self._on_config_global_changed()


def main():
    App().mainloop()
