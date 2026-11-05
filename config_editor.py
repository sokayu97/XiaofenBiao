"""
config_editor.py
配置编辑器：通过 GUI 直接编辑 configs/*.json
"""

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config import ExamConfig, Section


class SectionDialog(tk.Toplevel):
    def __init__(self, parent, title, section=None, on_ok=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_ok = on_ok

        self.prefix_var = tk.StringVar(value=section.prefix if section else "")
        self.type_var = tk.StringVar(value=section.type if section else "objective")
        self.count_var = tk.StringVar(value=str(section.count) if section else "")

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="题号前缀：").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.prefix_var, width=10).grid(row=0, column=1, pady=4)
        ttk.Label(frm, text="（如 一、二）", foreground="gray").grid(row=0, column=2, sticky="w", padx=4)

        ttk.Label(frm, text="题型：").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(frm, textvariable=self.type_var, state="readonly",
                     values=["objective", "subjective"], width=12).grid(row=1, column=1, pady=4)
        ttk.Label(frm, text="（objective=客观 / subjective=主观）",
                  foreground="gray").grid(row=1, column=2, sticky="w", padx=4)

        ttk.Label(frm, text="小题数：").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.count_var, width=10).grid(row=2, column=1, pady=4)

        btn = ttk.Frame(frm)
        btn.grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky="e")
        ttk.Button(btn, text="取消", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="确定", command=self._ok).pack(side="right", padx=4)

    def _ok(self):
        p = self.prefix_var.get().strip()
        t = self.type_var.get().strip()
        try:
            c = int(self.count_var.get().strip())
        except ValueError:
            messagebox.showerror("错误", "小题数必须是整数", parent=self)
            return
        if not p:
            messagebox.showerror("错误", "题号前缀不能为空", parent=self)
            return
        if c < 1:
            messagebox.showerror("错误", "小题数必须 >= 1", parent=self)
            return
        if self.on_ok:
            self.on_ok(Section(prefix=p, type=t, count=c))
        self.destroy()


class RuleDialog(tk.Toplevel):
    def __init__(self, parent, title, q="", rule="lt_zero", on_ok=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_ok = on_ok

        self.q_var = tk.StringVar(value=q)
        self.rule_var = tk.StringVar(value=rule or "lt_zero")

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="题号：").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.q_var, width=12).grid(row=0, column=1, pady=4)
        ttk.Label(frm, text="（如 二.16）", foreground="gray").grid(row=0, column=2, sticky="w", padx=4)

        ttk.Label(frm, text="规则：").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(frm, textvariable=self.rule_var, state="readonly",
                     values=["eq_zero", "lt_zero", "gt_zero"], width=12).grid(row=1, column=1, pady=4)

        btn = ttk.Frame(frm)
        btn.grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky="e")
        ttk.Button(btn, text="取消", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn, text="确定", command=self._ok).pack(side="right", padx=4)

    def _ok(self):
        q = self.q_var.get().strip()
        r = self.rule_var.get().strip()
        if not q:
            messagebox.showerror("错误", "题号不能为空", parent=self)
            return
        if self.on_ok:
            self.on_ok(q, r)
        self.destroy()


class ConfigEditor(tk.Toplevel):
    def __init__(self, parent, config_dir="configs", on_save=None):
        super().__init__(parent)
        self.title("配置管理")
        self.geometry("960x720")
        self.minsize(900, 680)
        self.transient(parent)
        self.grab_set()

        self.config_dir = config_dir
        self.on_save = on_save
        self.current_file = None
        self._files = []
        os.makedirs(config_dir, exist_ok=True)

        self.sections = []
        self.special_rules = {}

        self._build_ui()
        self._refresh_file_list()

    def _build_ui(self):
        main = ttk.Frame(self, padding=8)
        main.pack(fill="both", expand=True)

        # 左：配置文件列表
        left = ttk.LabelFrame(main, text="配置文件")
        left.pack(side="left", fill="y", padx=(0, 8))

        self.file_list = tk.Listbox(left, width=22, exportselection=False,
                                    font=("Consolas", 10))
        self.file_list.pack(fill="both", expand=True, padx=4, pady=4)
        self.file_list.bind("<<ListboxSelect>>", self._on_select_file)

        lbtn = ttk.Frame(left)
        lbtn.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(lbtn, text="新建", command=self._new_file).pack(
            side="left", fill="x", expand=True, padx=(0, 2))
        ttk.Button(lbtn, text="删除", command=self._delete_file).pack(
            side="left", fill="x", expand=True, padx=(2, 0))

        # 右：编辑区
        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)

        basic = ttk.LabelFrame(right, text="基本信息")
        basic.pack(fill="x", pady=(0, 6))

        self.name_var = tk.StringVar()
        self.grade_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.def_rule_var = tk.StringVar(value="eq_zero")
        self.auto_special_var = tk.StringVar(value="last_subjective")

        ttk.Label(basic, text="试卷名称：").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(basic, textvariable=self.name_var, width=18).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Label(basic, text="年级：").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(basic, textvariable=self.grade_var, width=16).grid(row=0, column=3, sticky="w", pady=4)

        ttk.Label(basic, text="标题模板：").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(basic, textvariable=self.title_var).grid(
            row=1, column=1, columnspan=3, sticky="ew", pady=4, padx=(0, 8))
        ttk.Label(basic, text="可用占位符：{grade}  {class_num}  {exam_name}  {subject}",
                  foreground="gray").grid(row=2, column=1, columnspan=3, sticky="w", padx=4)

        ttk.Label(basic, text="默认规则：").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        ttk.Combobox(basic, textvariable=self.def_rule_var, state="readonly",
                     values=["eq_zero", "lt_zero", "gt_zero"], width=14).grid(
            row=3, column=1, sticky="w", pady=4)
        ttk.Label(basic, text="自动特殊：").grid(row=3, column=2, sticky="w", padx=6, pady=4)
        ttk.Combobox(basic, textvariable=self.auto_special_var, state="readonly",
                     values=["last_subjective", ""], width=16).grid(
            row=3, column=3, sticky="w", pady=4)

        basic.columnconfigure(1, weight=1)

        # 大题
        sec_frame = ttk.LabelFrame(right, text="大题设置")
        sec_frame.pack(fill="x", pady=(0, 6))
        tb = ttk.Frame(sec_frame)
        tb.pack(fill="x", padx=4, pady=4)
        ttk.Button(tb, text="添加大题", command=self._add_section).pack(side="left")
        ttk.Button(tb, text="编辑", command=self._edit_section).pack(side="left", padx=4)
        ttk.Button(tb, text="删除", command=self._del_section).pack(side="left")

        cols = ("prefix", "type", "count")
        self.sec_tree = ttk.Treeview(sec_frame, columns=cols, show="headings", height=5)
        self.sec_tree.heading("prefix", text="前缀")
        self.sec_tree.heading("type", text="类型")
        self.sec_tree.heading("count", text="小题数")
        self.sec_tree.column("prefix", width=100, anchor="center")
        self.sec_tree.column("type", width=140, anchor="center")
        self.sec_tree.column("count", width=100, anchor="center")
        self.sec_tree.pack(fill="x", padx=4, pady=(0, 4))
        self.sec_tree.bind("<Double-1>", lambda e: self._edit_section())

        # 特殊规则
        rule_frame = ttk.LabelFrame(right, text="特殊规则（留空则按“自动特殊”推断）")
        rule_frame.pack(fill="x", pady=(0, 6))
        tb2 = ttk.Frame(rule_frame)
        tb2.pack(fill="x", padx=4, pady=4)
        ttk.Button(tb2, text="添加规则", command=self._add_rule).pack(side="left")
        ttk.Button(tb2, text="编辑", command=self._edit_rule).pack(side="left", padx=4)
        ttk.Button(tb2, text="删除", command=self._del_rule).pack(side="left")

        cols2 = ("q", "rule")
        self.rule_tree = ttk.Treeview(rule_frame, columns=cols2, show="headings", height=4)
        self.rule_tree.heading("q", text="题号")
        self.rule_tree.heading("rule", text="规则")
        self.rule_tree.column("q", width=100, anchor="center")
        self.rule_tree.column("rule", width=120, anchor="center")
        self.rule_tree.pack(fill="x", padx=4, pady=(0, 4))
        self.rule_tree.bind("<Double-1>", lambda e: self._edit_rule())

        # 底部
        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="关闭", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(bottom, text="另存为...", command=self._save_as).pack(side="right", padx=4)
        ttk.Button(bottom, text="保存", command=self._save).pack(side="right", padx=4)

    def _refresh_file_list(self):
        self.file_list.delete(0, "end")
        self._files = []
        if os.path.isdir(self.config_dir):
            for f in sorted(os.listdir(self.config_dir)):
                if f.endswith(".json"):
                    self._files.append(f)
                    self.file_list.insert("end", f)

    def _on_select_file(self, event=None):
        sel = self.file_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._files):
            return
        fname = self._files[idx]
        try:
            cfg = ExamConfig.from_file(os.path.join(self.config_dir, fname))
        except Exception as e:
            messagebox.showerror("错误", f"读取失败：{e}", parent=self)
            return
        self._load_config(cfg)
        self.current_file = fname

    def _load_config(self, cfg):
        self.name_var.set(cfg.name)
        self.grade_var.set(cfg.grade)
        self.title_var.set(cfg.title_template)
        self.def_rule_var.set(cfg.default_zero_rule)
        self.auto_special_var.set(cfg.auto_special or "")
        self.sections = list(cfg.sections)
        self.special_rules = dict(cfg.special_rules)
        self._refresh_sections()
        self._refresh_rules()

    def _refresh_sections(self):
        for i in self.sec_tree.get_children():
            self.sec_tree.delete(i)
        label = {"objective": "客观题", "subjective": "主观题"}
        for s in self.sections:
            self.sec_tree.insert("", "end",
                                 values=(s.prefix, label.get(s.type, s.type), s.count))

    def _refresh_rules(self):
        for i in self.rule_tree.get_children():
            self.rule_tree.delete(i)
        label = {"eq_zero": "= 0", "lt_zero": "< 0", "gt_zero": "> 0"}
        for q, r in self.special_rules.items():
            self.rule_tree.insert("", "end", values=(q, label.get(r, r)))

    def _add_section(self):
        def ok(sec):
            self.sections.append(sec)
            self._refresh_sections()
        SectionDialog(self, "添加大题", on_ok=ok)

    def _edit_section(self):
        sel = self.sec_tree.selection()
        if not sel:
            return
        idx = self.sec_tree.index(sel[0])
        old = self.sections[idx]
        def ok(sec):
            self.sections[idx] = sec
            self._refresh_sections()
        SectionDialog(self, "编辑大题", section=old, on_ok=ok)

    def _del_section(self):
        sel = self.sec_tree.selection()
        if not sel:
            return
        del self.sections[self.sec_tree.index(sel[0])]
        self._refresh_sections()

    def _add_rule(self):
        def ok(q, rule):
            self.special_rules[q] = rule
            self._refresh_rules()
        RuleDialog(self, "添加规则", on_ok=ok)

    def _edit_rule(self):
        sel = self.rule_tree.selection()
        if not sel:
            return
        idx = self.rule_tree.index(sel[0])
        q = list(self.special_rules.keys())[idx]
        rule = self.special_rules[q]
        def ok(new_q, new_rule):
            del self.special_rules[q]
            self.special_rules[new_q] = new_rule
            self._refresh_rules()
        RuleDialog(self, "编辑规则", q=q, rule=rule, on_ok=ok)

    def _del_rule(self):
        sel = self.rule_tree.selection()
        if not sel:
            return
        idx = self.rule_tree.index(sel[0])
        q = list(self.special_rules.keys())[idx]
        del self.special_rules[q]
        self._refresh_rules()

    def _collect_config(self):
        return ExamConfig(
            name=self.name_var.get().strip() or "未命名",
            grade=self.grade_var.get().strip() or "高三年级",
            title_template=self.title_var.get().strip()
                           or "{grade}{class_num}班{exam_name}考试{subject}成绩单",
            sections=list(self.sections),
            default_zero_rule=self.def_rule_var.get() or "eq_zero",
            special_rules=dict(self.special_rules),
            auto_special=self.auto_special_var.get() or "",
        )

    def _config_to_dict(self, cfg):
        return {
            "name": cfg.name,
            "grade": cfg.grade,
            "title_template": cfg.title_template,
            "sections": [{"prefix": s.prefix, "type": s.type, "count": s.count}
                         for s in cfg.sections],
            "default_zero_rule": cfg.default_zero_rule,
            "special_rules": cfg.special_rules,
            "auto_special": cfg.auto_special or None,
        }

    def _save(self):
        if not self.current_file:
            return self._save_as()
        path = os.path.join(self.config_dir, self.current_file)
        cfg = self._collect_config()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._config_to_dict(cfg), f, ensure_ascii=False, indent=2)
        if self.on_save:
            self.on_save()
        messagebox.showinfo("已保存", f"已保存到：\n{path}", parent=self)

    def _save_as(self):
        fname = filedialog.asksaveasfilename(
            title="另存为",
            initialdir=self.config_dir,
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not fname:
            return
        self.current_file = os.path.basename(fname)
        cfg = self._collect_config()
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(self._config_to_dict(cfg), f, ensure_ascii=False, indent=2)
        self._refresh_file_list()
        if self.on_save:
            self.on_save()
        messagebox.showinfo("已保存", f"已保存到：\n{fname}", parent=self)

    def _new_file(self):
        self.current_file = None
        self.name_var.set("新配置")
        self.grade_var.set("高三年级")
        self.title_var.set("{grade}{class_num}班{exam_name}考试{subject}成绩单")
        self.def_rule_var.set("eq_zero")
        self.auto_special_var.set("last_subjective")
        self.sections = []
        self.special_rules = {}
        self._refresh_sections()
        self._refresh_rules()

    def _delete_file(self):
        if not self.current_file:
            return
        if not messagebox.askyesno("确认", f"删除 {self.current_file}？", parent=self):
            return
        try:
            os.remove(os.path.join(self.config_dir, self.current_file))
        except Exception as e:
            messagebox.showerror("错误", str(e), parent=self)
            return
        self.current_file = None
        self._refresh_file_list()
        if self.on_save:
            self.on_save()
