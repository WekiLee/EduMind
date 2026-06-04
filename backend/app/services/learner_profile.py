"""学习者画像工具 —— 默认值 + 旧版扁平→新版嵌套归一化"""

DEFAULT_LEARNER_PROFILE = {
    "content": {
        "abstraction_level": 0.5,
        "analogy_density": 0.5,
        "example_style": 0.5,
    },
    "pace": {
        "teaching_speed": 0.5,
        "session_duration_min": 25,
        "repetition_preference": 0.5,
    },
    "interaction": {
        "feedback_tone": 0.5,
        "error_handling": 0.5,
        "interrupt_policy": "anytime",
    },
    "assessment": {
        "quiz_style": 0.5,
        "tolerance": 0.7,
        "review_frequency": 0.5,
    },
    "ui": {
        "font_size": "medium",
        "color_scheme": "standard",
        "layout_density": "standard",
        "enable_tts": False,
    },
}

# 旧版扁平字段 → (group, field) 映射，用于迁移
_FLAT_TO_NESTED = {
    "abstraction_level": ("content", "abstraction_level"),
    "analogy_density": ("content", "analogy_density"),
    "example_style": ("content", "example_style"),
    "teaching_speed": ("pace", "teaching_speed"),
    "session_duration": ("pace", "session_duration_min"),
    "session_duration_min": ("pace", "session_duration_min"),
    "repetition_preference": ("pace", "repetition_preference"),
    "feedback_tone": ("interaction", "feedback_tone"),
    "error_handling": ("interaction", "error_handling"),
    "quiz_style": ("assessment", "quiz_style"),
    "tolerance": ("assessment", "tolerance"),
    "review_frequency": ("assessment", "review_frequency"),
}


def normalize(profile: dict | None) -> dict:
    """
    将学习者画像归一化为标准嵌套结构。

    兼容旧版扁平格式（如 {"abstraction_level": 0.3, ...}）
    和已有嵌套格式，缺失字段用默认值填充。
    """
    if not profile:
        return dict(DEFAULT_LEARNER_PROFILE)

    # 检测是否为扁平结构（顶层含有 content/pace/interaction/assessment/ui 之外的字段）
    top_keys = set(profile.keys())
    group_keys = {"content", "pace", "interaction", "assessment", "ui"}

    if not top_keys.intersection(group_keys):
        # 旧版扁平格式 → 转为嵌套
        result = dict(DEFAULT_LEARNER_PROFILE)
        for flat_key, value in profile.items():
            mapping = _FLAT_TO_NESTED.get(flat_key)
            if mapping:
                group, field = mapping
                result[group][field] = value
        return result

    # 已有嵌套格式：按组填充缺失字段
    result = {}
    for group_name, default_group in DEFAULT_LEARNER_PROFILE.items():
        incoming_group = profile.get(group_name, {})
        if isinstance(incoming_group, dict):
            merged = dict(default_group)
            merged.update(incoming_group)
            result[group_name] = merged
        else:
            result[group_name] = dict(default_group)
    return result


def read(profile: dict | None, group: str, field: str):
    """
    从（已归一化的）profile 中安全读取嵌套字段。
    如果 profile 未归一化，自动归一化后再读。
    """
    norm = normalize(profile)
    group_data = norm.get(group, {})
    if isinstance(group_data, dict):
        return group_data.get(field, DEFAULT_LEARNER_PROFILE.get(group, {}).get(field))
    return DEFAULT_LEARNER_PROFILE.get(group, {}).get(field)
