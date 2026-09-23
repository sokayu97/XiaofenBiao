import os
import re
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Border, Side, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from datetime import datetime

# ====== 目录配置 ======
INPUT_DIR = "resources"
OUTPUT_DIR = "production"

# 如果目录不存在则创建
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 浅红填充
light_red = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
thin = Side(style="thin", color="000000")
medium = Side(style="medium", color="000000")


def clean_header(h):
    """清理表头：删去（共*分）、作答/答案、英文逗号"""
    h = str(h)
    h = re.sub(r"（共\d+分）", "", h)
    h = h.replace("作答/答案", "")
    h = h.replace(",", "")
    return h.strip()


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


def process_one(input_file, output_file):
    print(f"正在处理：{input_file}")

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

    # 2、3. 清理表头
    df.columns = [clean_header(c) for c in df.columns]

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

    # 写 Excel
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
                    cell.fill = light_red
            else:
                if isinstance(val, (int, float)) and val < 0:
                    cell.fill = light_red

    # 9. 框线
    for row in ws.iter_rows(min_row=header_row, max_row=max_row,
                            min_col=1, max_col=max_col):
        for cell in row:
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # 外侧加粗
    for col in range(1, max_col + 1):
        c = ws.cell(row=header_row, column=col)
        c.border = Border(left=c.border.left, right=c.border.right,
                          top=medium, bottom=c.border.bottom)
        c = ws.cell(row=max_row, column=col)
        c.border = Border(left=c.border.left, right=c.border.right,
                          top=c.border.top, bottom=medium)

    for row in range(header_row, max_row + 1):
        c = ws.cell(row=row, column=1)
        c.border = Border(left=medium, right=c.border.right,
                          top=c.border.top, bottom=c.border.bottom)
        c = ws.cell(row=row, column=max_col)
        c.border = Border(left=c.border.left, right=medium,
                          top=c.border.top, bottom=c.border.bottom)

    wb.save(output_file)
    print(f"已生成：{output_file}")


def main():
    # 支持的 Excel 后缀
    exts = (".xlsx", ".xls")

    files = [f for f in os.listdir(INPUT_DIR)
             if f.lower().endswith(exts) and not f.startswith("~$")]

    if not files:
        print(f"未在 {INPUT_DIR} 目录下找到任何 Excel 文件。")
        return

    for f in files:
        input_path = os.path.join(INPUT_DIR, f)
        name, ext = os.path.splitext(f)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(OUTPUT_DIR, f"{name}_处理后_{ts}{ext}")

        try:
            process_one(input_path, output_path)
        except Exception as e:
            print(f"处理 {f} 时出错：{e}")

        os.startfile(os.path.abspath(OUTPUT_DIR))  # 仅 Windows 可用

if __name__ == "__main__":
    main()
