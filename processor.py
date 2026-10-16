"""
processor.py
小分表批量处理逻辑（与界面无关）
"""

import os
import re
import traceback

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Border, Side, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

# ==================== 样式常量 ====================

LIGHT_RED = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
THIN = Side(style="thin", color="000000")
MEDIUM = Side(style="medium", color="000000")


# ==================== 工具函数 ====================

def clean_header(h):
    """清理表头：删去（共*分）、作答/答案、英文逗号"""
    h = str(h)
    h = re.sub(r"（共\d+分）", "", h)
    h = h.replace("作答/答案", "")
    h = h.replace(",", "")
    return h.strip()


def unique_headers(cols):
    """
    让表头唯一：
    - 形如 一.1 / 二.16 的列保持原样，并记住它作为"当前题号"
    - 形如单字母 A/B/C/D 的答案列，改成 "题号_选项"，如 一.1_D
    - 其它列（姓名、总、客、主、校、班等）原样保留
    """
    result = []
    last_q = None
    for c in cols:
        c = str(c).strip()
        if re.fullmatch(r"[一二三四五六七八九十]+\.\d+", c):
            last_q = c
            result.append(c)
        elif re.fullmatch(r"[A-Z]+", c) and last_q:
            result.append(f"{last_q}_{c}")
        else:
            result.append(c)
    return result


def to_num(x):
    """文本形式数字转数字"""
    if isinstance(x, str):
        s = x.strip()
        if s == "":
            return x
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        if re.fullmatch(r"-?\d+\.\d+", s):
            return float(s)
    return x


# ==================== 单文件处理 ====================

def process_one(input_file, output_file, log=print):
    """处理单个 Excel 文件，输出到 output_file"""
    log(f"正在处理：{os.path.basename(input_file)}")

    # 读取
    df = pd.read_excel(input_file, sheet_name="Worksheet", dtype=object)

    # 1. 删去学号、考号、班级
    for col in ["学号", "考号", "班级"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    # 4. 数据区删英文逗号
    df = df.apply(
        lambda col: col.map(lambda x: x.replace(",", "") if isinstance(x, str) else x)
    )

    # 2、3. 清理表头 + 唯一化
    df.columns = unique_headers([clean_header(c) for c in df.columns])

    # 7. 改列名
    df = df.rename(columns={
        "总分": "总",
        "客观题": "客",
        "主观题": "主",
        "学校排名": "校",
        "班级排名": "班"
    })

    # 5. 文本数字转数字
    df = df.apply(lambda col: col.map(to_num))

    # 6. 删去总分为 0 的行
    if "总" in df.columns:
        df = df[df["总"] != 0].reset_index(drop=True)

    # 写入 Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Worksheet"

    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    # 10. 第一行上方插入空行 → 表头变为第 2 行
    ws.insert_rows(1)

    header_row = 2
    max_row = ws.max_row
    max_col = ws.max_column

    # 8. 标红
    for row in ws.iter_rows(min_row=header_row + 1, max_row=max_row,
                            min_col=1, max_col=max_col):
        for cell in row:
            col_name = ws.cell(row=header_row, column=cell.column).value
            val = cell.value
            if col_name != "二.16":
                if val == 0:
                    cell.fill = LIGHT_RED
            else:
                if isinstance(val, (int, float)) and val < 0:
                    cell.fill = LIGHT_RED

    # 9. 框线
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

    for row in range(header_row, max_row + 1):
        c = ws.cell(row=row, column=1)
        c.border = Border(left=MEDIUM, right=c.border.right,
                          top=c.border.top, bottom=c.border.bottom)
        c = ws.cell(row=row, column=max_col)
        c.border = Border(left=c.border.left, right=MEDIUM,
                          top=c.border.top, bottom=c.border.bottom)

    wb.save(output_file)
    log(f"  ✅ 已生成：{os.path.basename(output_file)}")


# ==================== 批量处理 ====================

def batch_process(input_dir, output_dir, log=print, exts=(".xlsx", ".xls")):
    """
    批量处理 input_dir 下的所有 Excel 文件，输出到 output_dir。
    返回 (成功数, 失败数)。
    """
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
            process_one(input_path, output_path, log)
            ok += 1
        except Exception as e:
            fail += 1
            log(f"  ⚠️ 处理 {f} 失败：{e}")
            log(traceback.format_exc(limit=1))

    log(f"\n完成：成功 {ok} 个，失败 {fail} 个。")
    return ok, fail


# ==================== 命令行入口（可选） ====================

if __name__ == "__main__":
    import sys

    in_dir = sys.argv[1] if len(sys.argv) > 1 else "resources"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "production"
    batch_process(in_dir, out_dir)
