# 小分表处理工具

面向中学成绩单的自动化处理工具，用于批量清洗小分表、标注零分与负分、汇总各题错题名单、生成班级对比统计。支持通过配置文件适配不同学科和试卷结构。

![version](https://img.shields.io/badge/version-1.4.0-blue)
![python](https://img.shields.io/badge/python-3.8%2B-brightgreen)
![license](https://img.shields.io/badge/license-MIT-green)

---

## 目录

- [功能特性](#功能特性)
- [系统要求](#系统要求)
- [安装](#安装)
- [快速开始](#快速开始)
- [界面说明](#界面说明)
- [配置文件](#配置文件)
- [打包为 exe](#打包为-exe)
- [Windows 7 兼容性](#windows-7-兼容性)
- [常见问题](#常见问题)
- [目录结构](#目录结构)
- [作者与致谢](#作者与致谢)

---

## 功能特性

### 小分表单文件处理
- 选择单个小分表，按所选试卷配置自动清洗
- 删除学号、考号、班级列，统一表头格式
- 文本型数字转数字，删除总分为 0 的行
- **零分标红**：普通题得 0 分的单元格标浅红色
- **负分标红**：卷面分题（默认最后一道主观题）小于 0 分时标浅红色
- 生成「零分负分汇总」工作表，按题统计得 0 分 / 负分的学生名单
- 可选添加标题（跨列居中），如「高三年级8班四调考试物理成绩单」
- 列宽自适应，表头至数据区加细框线 + 外侧粗框线

### 小分表批量处理
- 对 `resources/` 目录批量执行上述处理
- 输出到 `production/` 目录，文件名自动加 `_处理后` 后缀
- 处理过程实时显示日志，单个文件失败不影响其它文件

### 班级对比处理
- 汇总各班客观题、主观题平均分
- 生成「处理后」工作表，含客观分、主观分、总分
- 原工作表自动规范化：百分比转小数（保留百分比显示格式），文本数字转数字

### 配置管理
- 图形界面增删改试卷配置，无需手动编辑 JSON
- 内置高中九科默认配置（河北高考结构）
- 支持自定义大题数量、题型、特殊规则、标题模板
- 配置切换后自动记住，下次启动沿用上次选择

---

## 系统要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows 7 SP1 / 10 / 11 |
| Python | 3.8 及以上（Windows 7 必须用 3.8） |
| 依赖库 | pandas、openpyxl、Pillow（可选，用于显示赞赏码） |

---

## 安装

### 1. 克隆或下载源码

```bash
git clone https://github.com/sokayu97/XiaofenBiao.git
cd XiaofenBiao
```

### 2. 创建虚拟环境（推荐）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> PowerShell 若提示禁止运行脚本，先执行：
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### 3. 安装依赖

```powershell
python -m pip install pandas openpyxl pillow
```

### 0. 或者直接下载发行版

请前往 [Releases](https://github.com/sokayu97/XiaofenBiao/releases) 页面，下载最新版本的 `小分表处理工具.exe` 即可直接运行（无需安装 Python）。
或者点击[该链接](https://github.com/sokayu97/XiaofenBiao/releases/download/v1.4.0/XiaofenBiao_v1.4.0.exe)直接下载。

---

## 快速开始

```powershell
python main.py
```

首次启动时，程序会：

1. 自动在 `configs/` 下生成高中九科默认配置（若目录为空）
2. 自动创建 `production/` 输出目录
3. 默认选中「物理」配置

### 基本流程

1. 把原始小分表（`.xlsx`）放入 `resources/`
2. 在对应选项卡选择配置、填写年级/考试名称/班级
3. 点击开始处理
4. 结果输出到 `production/`（批量）或用户指定路径（单文件）

---

## 界面说明

程序主界面为四个选项卡：

### 小分表单文件处理

| 控件             | 说明                                 |
|------------------|--------------------------------------|
| 试卷配置         | 选择学科配置，默认物理               |
| 年级             | 自动跟随配置，可临时覆盖             |
| 输入文件         | 选择单个 `.xlsx` 文件                |
| 考试名称 / 班级  | 用于生成标题，班级必须为纯数字       |
| 自动打开保存位置 | 处理完成后在资源管理器中选中生成文件 |
| 开始处理并保存   | 弹出保存对话框，确认后处理           |

### 小分表批量处理

| 控件               | 说明                   |
|--------------------|------------------------|
| 输入文件夹         | 默认 `resources/`      |
| 输出文件夹         | 默认 `production/`     |
| 自动打开输出文件夹 | 处理完成后打开输出目录 |
| 开始批量处理       | 后台线程处理全部文件   |

### 班级对比处理

| 控件             | 说明                           |
|------------------|--------------------------------|
| 输入文件         | 选择「班级对比」类 Excel       |
| 自动打开保存位置 | 处理完成后打开保存位置         |
| 开始处理并保存   | 生成含「处理后」工作表的新文件 |

生成的「处理后」工作表结构：

| 班级 | 一.1 | 一.2 | … | 二.16 | 客观分 | 主观分 | 总分  |
|------|------|------|---|-------|--------|--------|-------|
| 1    | 1.6  | 2.25 | … | 0     | 30.22  | 32.03  | 62.25 |

### 关于

显示版本信息、功能简介、作者信息、GitHub 链接，以及赞赏码入口。

---

## 配置文件

### 默认配置

首次启动时若 `configs/` 为空，程序会自动生成以下 9 份配置：

| 文件             | 科目 | 客观题 | 主观题（含卷面分） |
|------------------|------|--------|--------------------|
| `chinese.json`   | 语文 | 12     | 12                 |
| `math.json`      | 数学 | 14     | 6                  |
| `english.json`   | 英语 | 65     | 3                  |
| `physics.json`   | 物理 | 10     | 6                  |
| `chemistry.json` | 化学 | 14     | 5                  |
| `biology.json`   | 生物 | 18     | 6                  |
| `politics.json`  | 政治 | 16     | 5                  |
| `history.json`   | 历史 | 16     | 5                  |
| `geography.json` | 地理 | 16     | 4                  |

### 配置文件格式

```json
{
  "name": "物理",
  "grade": "高三年级",
  "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
  "sections": [
    { "prefix": "一", "type": "objective",  "count": 10 },
    { "prefix": "二", "type": "subjective", "count": 6 }
  ],
  "default_zero_rule": "eq_zero",
  "special_rules": { "二.16": "lt_zero" },
  "auto_special": null
}
```

### 字段说明

| 字段                | 说明                                                                     |
|---------------------|--------------------------------------------------------------------------|
| `name`              | 学科名称，用于标题中 `{subject}` 占位                                    |
| `grade`             | 默认年级，界面中可临时覆盖                                               |
| `title_template`    | 标题模板，支持 `{grade}` `{class_num}` `{exam_name}` `{subject}`         |
| `sections`          | 大题列表，按顺序排列                                                     |
| `sections[].prefix` | 题号前缀，如 `一`、`二`                                                  |
| `sections[].type`   | `objective`（客观题）/ `subjective`（主观题）                            |
| `sections[].count`  | 本大题小题数（含卷面分若在该大题末尾）                                   |
| `default_zero_rule` | 普通题的筛选规则                                                         |
| `special_rules`     | 特殊题规则，格式为 `{ "题号": "规则" }`                                  |
| `auto_special`      | 自动特殊：`last_subjective` 自动把最后一道主观题设为 `<0`；`null` 不自动 |

### 题号规则

- **全局连续编号**：题号按大题顺序全局递增
    - 例：`一(count=10)` + `二(count=6)` → `一.1~一.10`，`二.11~二.16`
- **卷面分为额外一题**：若某科有卷面分，把对应大题的 `count` 加 1，卷面分自动作为该大题最后一个题号

### 筛选规则

| 规则      | 含义     | 适用场景           |
|-----------|----------|--------------------|
| `eq_zero` | 得分 = 0 | 普通题的“零分”     |
| `lt_zero` | 得分 < 0 | 卷面分（负分扣分） |
| `gt_zero` | 得分 > 0 | 特殊正向筛选       |

### 通过 GUI 修改配置

点击选项卡右上角的「⚙ 管理配置」按钮：

- 左侧列出所有配置文件，可新建、删除
- 右侧编辑试卷名称、年级、标题模板、默认规则、大题列表、特殊规则
- 修改后点击「保存」或「另存为」
- 保存后所有选项卡的配置下拉框自动刷新

---

## 打包为 exe

### 环境准备

```powershell
python -m pip install pyinstaller pillow
```

### 打包命令

```powershell
python -m PyInstaller -F -w -n XiaofenBiao ^
    --collect-all pandas ^
    --collect-all openpyxl ^
    --collect-all PIL ^
    --add-data "assets;assets" ^
    main.py
```

- `-F`：单文件模式
- `-w`：不显示控制台窗口
- `--collect-all`：完整收集 pandas / openpyxl / PIL 依赖
- `--add-data`：把 `assets/` 目录打包进去（赞赏码等）

打包完成后，`dist/XiaofenBiao.exe` 即为可分发文件。

### 分发建议

把 exe 放到一个新文件夹，旁边建 `resources/` 目录：

```
分发目录/
├── XiaofenBiao.exe
├── resources/        （把待处理表放这里）
└── production/       （首次运行自动创建）
```

首次运行会自动生成 `configs/` 下的九科配置和 `app_state.json`（记住上次选中的配置）。

---

## Windows 7 兼容性

由于 Python 3.9+ 不再支持 Windows 7，若目标机器是 Win7，需要按以下方式处理：

### 打包端

1. 使用 **Python 3.8** 作为打包环境
2. 安装兼容的 PyInstaller（推荐 5.x 稳定版）

### 目标端

1. 确保 Win7 已安装 SP1
2. 安装补丁 **KB2533623**（Python 3.7+ 必需）
3. 安装 **Microsoft Visual C++ 2015-2022 Redistributable**（x86 和 x64 都装）
4. 如仍报错，尝试右键 exe → 属性 → 兼容性 → 以「Windows Vista SP2」模式运行

---

## 常见问题

### Q1：批量处理日志显示“成功 0，失败 0”

`resources/` 目录下没有 `.xlsx` / `.xls` 文件，或文件以 `~$` 开头（Excel 临时文件，自动跳过）。

### Q2：处理失败，提示“未找到表头行”

输入的不是标准小分表，或表头缺少“姓名 / 总分 / 客观题 / 主观题”等关键列。

### Q3：标红位置不对

检查配置中的 `default_zero_rule` 和 `special_rules`。卷面分题号必须出现在 `sections` 定义的题号范围内。

### Q4：答案列识别不出来

`clean_header` 中的关键词 `作答/答案` 是硬编码。若实际表头不含此词，需要修改 `processor.py` 的 `clean_header` 函数。

### Q5：Windows 提示“无法验证发布者”

PyInstaller 打包的 exe 无数字签名，系统 SmartScreen 会拦截。点击「更多信息」→「仍要运行」即可。

### Q6：打包后 exe 体积过大（200MB+）

pandas + numpy + openpyxl 组合较大，属正常现象。如需减小：

- 用文件夹模式代替 `-F`（启动更快，总体积更小）
- 用 `--noupx` 关闭压缩
- 剔除未使用的 pandas 子模块（较复杂，不推荐新手操作）

### Q7：升级 Python 或依赖后 Win7 打不开

Win7 用户请**固定使用 Python 3.8 及兼容依赖版本**打包，避免使用新版 Python。

### Q8：配置文件修改后不生效

关闭程序重新打开，或在「⚙ 管理配置」中保存后，主界面下拉框会自动刷新。若仍未生效，检查 `configs/` 下是否有同名的旧 JSON 冲突。

---

## 目录结构

```
XiaofenBiao/
├── main.py                 # 程序入口
├── processor.py            # 处理逻辑（无界面依赖）
├── config.py               # 配置数据结构与默认配置
├── config_editor.py        # 配置编辑器 GUI
├── gui.py                  # 主界面
├── app_state.json          # 运行时生成：记住上次配置
├── README.md
├── assets/
│   └── reward.png          # 赞赏码（可选）
├── configs/                # 试卷配置 JSON
│   ├── chinese.json
│   ├── math.json
│   ├── english.json
│   ├── physics.json
│   ├── chemistry.json
│   ├── biology.json
│   ├── politics.json
│   ├── history.json
│   └── geography.json
├── resources/              # 原始小分表
└── production/             # 处理结果输出
```

---

## 作者与致谢

**作者**：[瑜子sokayu97](https://github.com/sokayu97)  
**开发助手**：DeepSeek (深度求索)  
**技术栈**：Python · pandas · openpyxl · tkinter

如本项目对你有帮助，欢迎 Star 支持，或通过「关于 → 赞赏支持」请作者喝杯咖啡 ☕

### License

MIT License

---

## 版本历史

### v0.1.0
- 直接执行代码处理
- 实现小分表的批量处理

### v1.0.0
- 首个稳定版本
- 支持小分表单文件 / 批量处理
- 配备了图形化界面

### v1.1.0
- 支持小分表单文件 / 批量处理
- 新增了对班级对比表汇总的支持

### v1.2.0
- 支持小分表单文件 / 批量处理
- 支持班级对比表汇总
- 新增了配置管理，适用范围从高三物理扩展到各年级各学科

### v1.3.0
- 支持小分表单文件 / 批量处理
- 支持班级对比表汇总
- 图形化配置管理
- 内置高中九科配置
- 配置切换持久化

### v1.4.0
- 首个发布版
- 支持小分表单文件 / 批量处理
- 支持班级对比表汇总
- 图形化配置管理
- 内置高中九科配置
- 配置切换持久化
- 实现了对 Windows 7 的兼容
