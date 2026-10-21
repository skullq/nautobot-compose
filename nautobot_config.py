import os
from nautobot.core.settings import *

# 최신 스펙에 맞추어 플러그인 모듈 등록 (언더바 규칙 엄수)
PLUGINS = [
    "nautobot_plugin_nornir",
    "nautobot_golden_config",
    "nautobot_topology_views",
    "nautobot_ssot",
]

# Golden Configuration, Topology Views, SSoT 앱 구동 세부 설정
PLUGINS_CONFIG = {
    "nautobot_plugin_nornir": {
        "nornir_settings": {
            "credentials": "nautobot_plugin_nornir.plugins.credentials.nautobot_secrets.CredentialsNautobotSecrets",
        },
    },
    "nautobot_golden_config": {
        "enable_intended": True,   # 설계된 표준 설정(Intended Config) 생성 기능 활성화
        "enable_compliance": True, # 라우팅/ACL 분석 및 컴플라이언스 기능 활성화
        "enable_backup": True,     # 장비 CLI 설정 파일 백업 기능 활성화
    },
    "nautobot_topology_views": {
        "allow_coordinates_saving": True,
        "always_save_coordinates": False,
    },
    "nautobot_ssot": {
        "hide_example_jobs": False,
    },
}

