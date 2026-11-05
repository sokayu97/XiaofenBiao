"""
processor.py
小分表处理逻辑（与界面无关）
"""

import os
import re
import traceback
import unicodedata

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Border, Side, PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows

from config import ExamConfig, default_config

LIGHT_RED = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
THIN = Side(style="thin", color="000000")
MEDIUM = Side(style="medium", color="000000")


# ==================== 工具函数 ====================

def clean_header(h):
    h = str(h)
    h = re.sub(r"（共\d+分）", "", h)
    h = h.replace("作答/答案", "")
    h = h.replace(",", "")
    return h.strip()


def unique_headers(cols):
    """统一表头：纯题号保留，答案列变 '小题号.答案'"""
    result = []
    last_q_num = None
    for c in cols:
        c = str(c).strip()
        m = re.fullmatch(r"[一二三四五六七八九十]+\.(\d+)_([A-Z]+)", c)
        if m:
            q_num, ans = m.group(1), m.group(2)
            last_q_num = q_num
            result.append(f"{q_num}.{ans}")
            continue
        m = re.fullmatch(r"[一二三四五六七八九十]+\.(\d+)", c)
        if m:
            last_q_num = m.group(1)
            result.append(c)
            continue
        m = re.fullmatch(r"([A-Z]+)(?:\.\d+)?", c)
        if m and last_q_num:
            result.append(f"{last_q_num}.{m.group(1)}")
            continue
        result.append(c)
    return result


def strip_prefix_from_answer_headers(ws, header_row=2):
    """把 '1.D' → 'D'，纯题号列（中文开头）不动"""
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(row=header_row, column=col)
        val = cell.value
        if isinstance(val, str):
            m = re.fullmatch(r"\d+\.([A-Z]+)", val)
            if m:
                cell.value = m.group(1)


def to_num(x):
    if isinstance(x, str):
        s = x.strip()
        if s == "":
            return x
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        if re.fullmatch(r"-?\d+\.\d+", s):
            return float(s)
    return x


def auto_fit_columns(ws, min_width=4, max_width=60, padding=2):
    def display_width(s):
        w = 0
        for ch in str(s):
            if unicodedata.east_asian_width(ch) in ("W", "F"):
                w += 2
            else:
                w += 1
        return w

    for col_idx in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col_idx)
        max_w = 0
        for row_idx in range(1, ws.max_row + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            if cell.value is None:
                continue
            for line in str(cell.value).split("\n"):
                max_w = max(max_w, display_width(line))
        width = max(min_width, min(max_w + padding, max_width))
        ws.column_dimensions[col_letter].width = width


# ==================== 零分负分汇总 ====================

def summarize_zero_scores(df, cfg=None):
    if cfg is None:
        cfg = default_config()
    if "姓名" not in df.columns:
        return pd.DataFrame()
    if "总" in df.columns:
        df = df[df["总"] != 0]

    q_cols = [c for c in cfg.all_question_columns() if c in df.columns]
    special = cfg.effective_special_rules()
    rule_label = {"eq_zero": "= 0", "lt_zero": "< 0", "gt_zero": "> 0"}

    def apply_rule(series, rule):
        if rule == "lt_zero":
            return series < 0
        if rule == "gt_zero":
            return series > 0
        return series == 0

    rows = []
    for q in q_cols:
        rule = special.get(q, cfg.default_zero_rule)
        mask = apply_rule(df[q], rule)
        students = df.loc[mask, "姓名"].dropna().astype(str)
        students = [s.strip() for s in students if s.strip()]
        rows.append({
            "题号": q,
            "筛选规则": rule_label.get(rule, rule),
            "人数": len(students),
            "学生名单": "、".join(students) if students else "（无）",
        })
    return pd.DataFrame(rows)


# ==================== 单文件处理 ====================

def process_one(input_file, output_file, log=print, exam_name="", class_num="",
                grade="", cfg=None):
    if cfg is None:
        cfg = default_config()
    if not grade:
        grade = cfg.grade

    log(f"正在处理：{os.path.basename(input_file)}")

    df = pd.read_excel(input_file, sheet_name="Worksheet", dtype=object)

    for col in ["学号", "考号", "班级"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    df = df.apply(
        lambda col: col.map(lambda x: x.replace(",", "") if isinstance(x, str) else x)
    )

    df.columns = unique_headers([clean_header(c) for c in df.columns])

    df = df.rename(columns={
        "总分": "总", "客观题": "客", "主观题": "主",
        "学校排名": "校", "班级排名": "班",
    })

    df = df.apply(lambda col: col.map(to_num))

    if "总" in df.columns:
        df = df[df["总"] != 0].reset_index(drop=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Worksheet"
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    ws.insert_rows(1)

    header_row = 2
    strip_prefix_from_answer_headers(ws, header_row=header_row)
    max_row = ws.max_row
    max_col = ws.max_column

    # 标红
    special = cfg.effective_special_rules()
    for row in ws.iter_rows(min_row=header_row + 1, max_row=max_row,
                            min_col=1, max_col=max_col):
        for cell in row:
            col_name = ws.cell(row=header_row, column=cell.column).value
            val = cell.value
            rule = special.get(col_name, cfg.default_zero_rule)
            if rule == "lt_zero":
                if isinstance(val, (int, float)) and val < 0:
                    cell.fill = LIGHT_RED
            elif rule == "gt_zero":
                if isinstance(val, (int, float)) and val > 0:
                    cell.fill = LIGHT_RED
            else:
                if val == 0:
                    cell.fill = LIGHT_RED

    # 框线（表头 → 数据区）
    for row in ws.iter_rows(min_row=header_row, max_row=max_row,
                            min_col=1, max_col=max_col):
        for cell in row:
            cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    for col in range(1, max_col + 1):
        c = ws.cell(row=header_row, column=col)
        c.border = Border(left=c.border.left, right=c.border.right,
                          top=MEDIUM, bottom=c.border.bottom)
        c = ws.cell(row=max_row, column=col)
        c.border = Border(left=c.border.left, right=c.border.right,
                          top=c.border.top, bottom=MEDIUM)

    for r in range(header_row, max_row + 1):
        c = ws.cell(row=r, column=1)
        c.border = Border(left=MEDIUM, right=c.border.right,
                          top=c.border.top, bottom=c.border.bottom)
        c = ws.cell(row=r, column=max_col)
        c.border = Border(left=c.border.left, right=MEDIUM,
                          top=c.border.top, bottom=c.border.bottom)

    # 列宽自适应（A1 还空，不受标题影响）
    auto_fit_columns(ws)

    # 标题：跨列居中，不合并、不改列宽
    if exam_name or class_num or grade:
        title = cfg.build_title(exam_name=exam_name,
                                class_num=class_num,
                                grade=grade)
        cell = ws.cell(row=1, column=1)
        cell.value = title
        cell.alignment = Alignment(horizontal="centerContinuous",
                                   vertical="center")
        cell.font = Font(size=14, bold=True)

    # 零分负分汇总
    summary_df = summarize_zero_scores(df, cfg=cfg)
    if not summary_df.empty:
        ws2 = wb.create_sheet("零分负分汇总")
        for r in dataframe_to_rows(summary_df, index=False, header=True):
            ws2.append(r)
        for cell in ws2[1]:
            cell.font = Font(bold=True)

        for row in ws2.iter_rows(min_row=2, max_row=ws2.max_row,
                                 min_col=1, max_col=4):
            if row[0].value in special:
                for cell in row:
                    cell.fill = LIGHT_RED

        for row in ws2.iter_rows(min_row=1, max_row=ws2.max_row,
                                 min_col=1, max_col=4):
            for cell in row:
                cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

        auto_fit_columns(ws2, max_width=200)

    wb.save(output_file)
    log(f"  ✅ 已生成：{os.path.basename(output_file)}")


# ==================== 批量处理 ====================

def batch_process(input_dir, output_dir, log=print, exts=(".xlsx", ".xls"),
                  exam_name="", class_num="", grade="", cfg=None):
    if cfg is None:
        cfg = default_config()

    os.makedirs(output_dir, exist_ok=True)
    files = [f for f in os.listdir(input_dir)
             if f.lower().endswith(exts) and not f.startswith("~$")]
    if not files:
        log(f"❌ 未在 {input_dir} 找到任何 Excel 文件")
        return 0, 0

    ok, fail = 0, 0
    for f in files:
        input_path = os.path.join(input_dir, f)
        name, ext = os.path.splitext(f)
        output_path = os.path.join(output_dir, f"{name}_处理后{ext}")
        try:
            process_one(input_path, output_path, log,
                        exam_name=exam_name, class_num=class_num,
                        grade=grade, cfg=cfg)
            ok += 1
        except Exception as e:
            fail += 1
            log(f"  ⚠️ 处理 {f} 失败：{e}")
            log(traceback.format_exc(limit=1))

    log(f"\n完成：成功 {ok} 个，失败 {fail} 个。")
    return ok, fail


# ==================== 班级对比处理 ====================

def process_class_compare(input_file, output_file, log=print, cfg=None):
    if cfg is None:
        cfg = default_config()

    log(f"正在处理班级对比表：{os.path.basename(input_file)}")
    wb = load_workbook(input_file)
    ws_src = wb.active
    rows = list(ws_src.iter_rows(values_only=True))

    valid_qs = set(cfg.all_question_columns())

    def q_name_of(header_text):
        m = re.search(r'([一二三四五六七八九十]+\.\d+)', str(header_text))
        if m and m.group(1) in valid_qs:
            return m.group(1)
        return None

    def section_type_of(q_name):
        prefix = q_name.split(".")[0]
        for sec in cfg.sections:
            if sec.prefix == prefix:
                return sec.type
        return "objective"

    header_indices = []
    for i, row in enumerate(rows):
        if row and len(row) >= 1 and str(row[0]).strip() == "班级":
            if any(cell is not None and "平均分" in str(cell) for cell in row):
                header_indices.append(i)
    if not header_indices:
        raise ValueError("未找到表头行（第一列为“班级”且包含“平均分”的列）")

    parsed_blocks = []
    for hi in header_indices:
        header = rows[hi]
        data = []
        j = hi + 1
        while j < len(rows):
            r = rows[j]
            if r is None or all(cell is None or str(cell).strip() == "" for cell in r):
                break
            if j in header_indices:
                break
            if str(r[0]).strip() == "主观题":
                j += 1
                continue
            data.append(r)
            j += 1

        keep_cols = []
        for idx, cell in enumerate(header):
            if cell is None:
                continue
            s = str(cell).strip()
            if s == "班级":
                keep_cols.append((idx, "班级"))
            elif "平均分" in s:
                q = q_name_of(s)
                if q:
                    keep_cols.append((idx, q))
        if not keep_cols:
            continue

        questions = [name for _, name in keep_cols if name != "班级"]
        if not questions:
            continue

        first_q = questions[0]
        block_type = "客观" if section_type_of(first_q) == "objective" else "主观"

        data_dict = {}
        for row in data:
            if row is None:
                continue
            d = {}
            cls_val = None
            for idx, name in keep_cols:
                val = row[idx] if idx < len(row) else None
                if name == "班级":
                    cls_val = val
                    d["班级"] = val
                else:
                    d[name] = to_num(val) if val is not None else None
            if cls_val is None:
                continue
            key = str(cls_val).strip()
            if not key:
                continue
            data_dict[key] = d

        parsed_blocks.append({
            'type': block_type,
            'questions': questions,
            'data': data_dict,
        })

    class_order = []
    for block in parsed_blocks:
        for cls in block['data'].keys():
            if cls not in class_order:
                class_order.append(cls)

    class_data = {}
    for cls in class_order:
        class_data[cls] = {'客观': {}, '主观': {}, '客观分': 0, '主观分': 0}

    for block in parsed_blocks:
        btype = block['type']
        for cls, d in block['data'].items():
            if cls not in class_data:
                class_data[cls] = {'客观': {}, '主观': {}, '客观分': 0, '主观分': 0}
            for q in block['questions']:
                val = d.get(q)
                class_data[cls][btype][q] = val if isinstance(val, (int, float)) else 0
            total = sum(v for v in class_data[cls][btype].values()
                        if isinstance(v, (int, float)))
            class_data[cls][f"{btype}分"] = total

    obj_questions = []
    subj_questions = []
    for block in parsed_blocks:
        if block['type'] == '客观':
            for q in block['questions']:
                if q not in obj_questions:
                    obj_questions.append(q)
        else:
            for q in block['questions']:
                if q not in subj_questions:
                    subj_questions.append(q)

    if "处理后" in wb.sheetnames:
        del wb["处理后"]
    ws_out = wb.create_sheet("处理后")

    headers = (["班级"] + obj_questions + subj_questions
               + ["客观分", "主观分", "总分"])
    ws_out.append(headers)

    for cls in class_order:
        cd = class_data[cls]
        row = [cls]
        for q in obj_questions:
            row.append(cd['客观'].get(q, ""))
        for q in subj_questions:
            row.append(cd['主观'].get(q, ""))
        obj = cd['客观分']
        subj = cd['主观分']
        row.append(obj)
        row.append(subj)
        row.append(obj + subj)
        ws_out.append(row)

    for cell in ws_out[1]:
        cell.font = Font(bold=True)

    max_row = ws_out.max_row
    max_col = ws_out.max_column
    for row in ws_out.iter_rows(min_row=1, max_row=max_row,
                                min_col=1, max_col=max_col):
        for cell in row:
            cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    for col in range(1, max_col + 1):
        c = ws_out.cell(row=1, column=col)
        c.border = Border(left=c.border.left, right=c.border.right,
                          top=MEDIUM, bottom=c.border.bottom)
        c = ws_out.cell(row=max_row, column=col)
        c.border = Border(left=c.border.left, right=c.border.right,
                          top=c.border.top, bottom=MEDIUM)

    for r in range(1, max_row + 1):
        c = ws_out.cell(row=r, column=1)
        c.border = Border(left=MEDIUM, right=c.border.right,
                          top=c.border.top, bottom=c.border.bottom)
        c = ws_out.cell(row=r, column=max_col)
        c.border = Border(left=c.border.left, right=MEDIUM,
                          top=c.border.top, bottom=c.border.bottom)

    auto_fit_columns(ws_out)

    # 客观分 / 主观分 等宽（取较窄）
    try:
        obj_idx = headers.index("客观分") + 1
        subj_idx = headers.index("主观分") + 1
        obj_w = ws_out.column_dimensions[get_column_letter(obj_idx)].width or 0
        subj_w = ws_out.column_dimensions[get_column_letter(subj_idx)].width or 0
        target = min(obj_w, subj_w)
        ws_out.column_dimensions[get_column_letter(obj_idx)].width = target
        ws_out.column_dimensions[get_column_letter(subj_idx)].width = target
    except ValueError:
        pass

    # 原工作表：文本数字 / 百分比转数字（A 列班级除外）
    for row in ws_src.iter_rows():
        for cell in row:
            if cell.column == 1:
                continue
            val = cell.value
            if not isinstance(val, str):
                continue
            s = val.strip()
            if s == "":
                continue

            if s.endswith("%"):
                core = s.rstrip("%")
                try:
                    num = float(core)
                except ValueError:
                    continue
                if "." in core:
                    dec = len(core.split(".")[1])
                    fmt = "0." + ("0" * dec) + "%"
                else:
                    fmt = "0%"
                cell.value = num / 100.0
                cell.number_format = fmt
                continue

            new_val = to_num(s)
            if isinstance(new_val, (int, float)):
                cell.value = new_val

    wb.save(output_file)
    log(f"  ✅ 已生成：{os.path.basename(output_file)}")


if __name__ == "__main__":
    import sys
    in_dir = sys.argv[1] if len(sys.argv) > 1 else "resources"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "production"
    batch_process(in_dir, out_dir)
