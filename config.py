"""
config.py
试卷配置：定义每份试卷的大题结构、题型、特殊筛选规则和标题模板
题号全局连续：一.1~一.N 接 二.(N+1)~二.M ...
卷面分为最后一个主观题的额外一题，由 auto_special 自动识别
"""

import json
import os
from dataclasses import dataclass, field


@dataclass
class Section:
    prefix: str
    type: str
    count: int


@dataclass
class ExamConfig:
    name: str = "物理"
    grade: str = "高三年级"
    title_template: str = "{grade}{class_num}班{exam_name}考试{subject}成绩单"
    sections: list = field(default_factory=list)
    default_zero_rule: str = "eq_zero"
    special_rules: dict = field(default_factory=dict)
    auto_special: str = "last_subjective"

    @classmethod
    def from_dict(cls, data):
        sections = [Section(**s) for s in data.get("sections", [])]
        return cls(
            name=data.get("name", "物理"),
            grade=data.get("grade", "高三年级"),
            title_template=data.get(
                "title_template",
                "{grade}{class_num}班{exam_name}考试{subject}成绩单",
            ),
            sections=sections,
            default_zero_rule=data.get("default_zero_rule", "eq_zero"),
            special_rules=data.get("special_rules", {}),
            auto_special=data.get("auto_special", "last_subjective"),
        )

    @classmethod
    def from_file(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def _iter_question_numbers(self):
        num = 1
        for sec in self.sections:
            for _ in range(sec.count):
                yield sec, sec.prefix, num
                num += 1

    def all_question_columns(self):
        return [f"{prefix}.{n}" for _, prefix, n in self._iter_question_numbers()]

    def objective_columns(self):
        return [f"{prefix}.{n}" for sec, prefix, n in self._iter_question_numbers()
                if sec.type == "objective"]

    def subjective_columns(self):
        return [f"{prefix}.{n}" for sec, prefix, n in self._iter_question_numbers()
                if sec.type == "subjective"]

    def effective_special_rules(self):
        rules = dict(self.special_rules)
        if not rules and self.auto_special == "last_subjective":
            subj = self.subjective_columns()
            if subj:
                rules[subj[-1]] = "lt_zero"
        return rules

    def build_title(self, exam_name="", class_num="", grade=None):
        return self.title_template.format(
            grade=grade if grade else self.grade,
            exam_name=exam_name,
            class_num=class_num,
            subject=self.name,
        )


# ==================== 九科默认配置 ====================

DEFAULT_SUBJECT_CONFIGS = [
    {"name": "语文", "grade": "高三年级",
     "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
     "sections": [{"prefix": "一", "type": "objective", "count": 12},
                  {"prefix": "二", "type": "subjective", "count": 12}],
     "default_zero_rule": "eq_zero", "special_rules": {},
     "auto_special": "last_subjective"},
    {"name": "数学", "grade": "高三年级",
     "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
     "sections": [{"prefix": "一", "type": "objective", "count": 14},
                  {"prefix": "二", "type": "subjective", "count": 6}],
     "default_zero_rule": "eq_zero", "special_rules": {},
     "auto_special": "last_subjective"},
    {"name": "英语", "grade": "高三年级",
     "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
     "sections": [{"prefix": "一", "type": "objective", "count": 65},
                  {"prefix": "二", "type": "subjective", "count": 3}],
     "default_zero_rule": "eq_zero", "special_rules": {},
     "auto_special": "last_subjective"},
    {"name": "物理", "grade": "高三年级",
     "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
     "sections": [{"prefix": "一", "type": "objective", "count": 10},
                  {"prefix": "二", "type": "subjective", "count": 6}],
     "default_zero_rule": "eq_zero", "special_rules": {},
     "auto_special": "last_subjective"},
    {"name": "化学", "grade": "高三年级",
     "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
     "sections": [{"prefix": "一", "type": "objective", "count": 14},
                  {"prefix": "二", "type": "subjective", "count": 5}],
     "default_zero_rule": "eq_zero", "special_rules": {},
     "auto_special": "last_subjective"},
    {"name": "生物", "grade": "高三年级",
     "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
     "sections": [{"prefix": "一", "type": "objective", "count": 18},
                  {"prefix": "二", "type": "subjective", "count": 6}],
     "default_zero_rule": "eq_zero", "special_rules": {},
     "auto_special": "last_subjective"},
    {"name": "政治", "grade": "高三年级",
     "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
     "sections": [{"prefix": "一", "type": "objective", "count": 16},
                  {"prefix": "二", "type": "subjective", "count": 5}],
     "default_zero_rule": "eq_zero", "special_rules": {},
     "auto_special": "last_subjective"},
    {"name": "历史", "grade": "高三年级",
     "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
     "sections": [{"prefix": "一", "type": "objective", "count": 16},
                  {"prefix": "二", "type": "subjective", "count": 5}],
     "default_zero_rule": "eq_zero", "special_rules": {},
     "auto_special": "last_subjective"},
    {"name": "地理", "grade": "高三年级",
     "title_template": "{grade}{class_num}班{exam_name}考试{subject}成绩单",
     "sections": [{"prefix": "一", "type": "objective", "count": 16},
                  {"prefix": "二", "type": "subjective", "count": 4}],
     "default_zero_rule": "eq_zero", "special_rules": {},
     "auto_special": "last_subjective"},
]


def default_config():
    """内置默认：物理"""
    return ExamConfig.from_dict(DEFAULT_SUBJECT_CONFIGS[3])


def pick_default_key(configs):
    """优先选择 name 为“物理”的配置；否则选第一个"""
    for k, cfg in configs.items():
        if getattr(cfg, "name", "") == "物理":
            return k
    return next(iter(configs)) if configs else ""


def create_default_configs(config_dir="configs"):
    os.makedirs(config_dir, exist_ok=True)
    existing = [f for f in os.listdir(config_dir) if f.endswith(".json")]
    if existing:
        return
    filenames = {
        "语文": "chinese.json", "数学": "math.json", "英语": "english.json",
        "物理": "physics.json", "化学": "chemistry.json", "生物": "biology.json",
        "政治": "politics.json", "历史": "history.json", "地理": "geography.json",
    }
    for cfg_dict in DEFAULT_SUBJECT_CONFIGS:
        fname = filenames.get(cfg_dict["name"], f"{cfg_dict['name']}.json")
        with open(os.path.join(config_dir, fname), "w", encoding="utf-8") as f:
            json.dump(cfg_dict, f, ensure_ascii=False, indent=2)


def load_configs(config_dir="configs"):
    result = {}
    if not os.path.isdir(config_dir):
        return result
    for f in sorted(os.listdir(config_dir)):
        if not f.endswith(".json"):
            continue
        try:
            cfg = ExamConfig.from_file(os.path.join(config_dir, f))
            key = f"{cfg.name}（{os.path.splitext(f)[0]}）"
            result[key] = cfg
        except Exception as e:
            print(f"跳过无效配置 {f}: {e}")
    return result
