"""领域配置文件加载 —— 带缓存，消除 quiz.py 与 ws/chat.py 的重复"""

import os
import time

import yaml

_domain_profile_cache: dict[str, tuple[dict, float]] = {}
_PROFILE_CACHE_TTL = 300  # 5 分钟


def load_domain_profile(domain_id: str) -> dict:
    """加载领域配置（带缓存，最多 _PROFILE_CACHE_TTL 秒重新读盘一次）"""
    now = time.time()
    cached = _domain_profile_cache.get(domain_id)
    if cached and (now - cached[1]) < _PROFILE_CACHE_TTL:
        return cached[0]

    path = os.path.join("app", "domain_profiles", f"{domain_id}.yaml")
    if not os.path.exists(path):
        path = os.path.join("app", "domain_profiles", "general.yaml")
        domain_id = "general"

    with open(path, encoding="utf-8") as f:
        profile = yaml.safe_load(f)

    _domain_profile_cache[domain_id] = (profile, now)
    return profile
