#!/usr/bin/env python3
"""
Nautobot Golden Configuration 로컬 저장소, 30분 주기 백업 및 파싱(컴플라이언스) 규칙 자동 설정 스크립트
1. 로컬 Git 저장소(local-cisco-backup) 연결
2. Golden Config Default Settings에 로컬 백업 저장소 및 백업 경로(템플릿) 설정
3. Cisco 라우팅(Static/BGP/OSPF/EIGRP/ISIS), 인터페이스, ACL, Route-Map, PBR 파싱 규칙(Feature & Rule) 자동 생성
4. 백업 잡(Backup Configurations) 및 파싱 잡(Perform Configuration Compliance) 활성화
5. 30분 주기 자동 백업 스케줄 등록
"""

import os
import sys
import subprocess
import requests

BASE_URL = os.environ.get("NAUTOBOT_URL", "http://127.0.0.1:8888/api").rstrip("/")
TOKEN = os.environ.get("NAUTOBOT_TOKEN", "0123456789abcdef0123456789abcdef01234567")
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# 파싱 대상 기능 및 매칭 규칙 정의 (Cisco IOS / IOS-XE 기준)
COMPLIANCE_RULES = [
    {
        "name": "Interfaces",
        "slug": "interfaces",
        "description": "인터페이스 설정 및 IP 주소 파싱",
        "match_config": "interface",
        "config_ordered": False,
    },
    {
        "name": "Static Routing",
        "slug": "static-routing",
        "description": "IPv4/IPv6 정적 라우팅 설정 파싱",
        "match_config": "ip route",
        "config_ordered": False,
    },
    {
        "name": "BGP Routing",
        "slug": "bgp-routing",
        "description": "BGP 라우팅 프로토콜 설정 파싱",
        "match_config": "router bgp",
        "config_ordered": False,
    },
    {
        "name": "OSPF Routing",
        "slug": "ospf-routing",
        "description": "OSPF 라우팅 프로토콜 설정 파싱",
        "match_config": "router ospf",
        "config_ordered": False,
    },
    {
        "name": "EIGRP Routing",
        "slug": "eigrp-routing",
        "description": "EIGRP 라우팅 프로토콜 설정 파싱",
        "match_config": "router eigrp",
        "config_ordered": False,
    },
    {
        "name": "IS-IS Routing",
        "slug": "isis-routing",
        "description": "IS-IS 라우팅 프로토콜 설정 파싱",
        "match_config": "router isis",
        "config_ordered": False,
    },
    {
        "name": "Access-Lists",
        "slug": "access-lists",
        "description": "표준/확장 Access-List (ACL) 파싱",
        "match_config": "ip access-list",
        "config_ordered": True,
    },
    {
        "name": "Route-Maps",
        "slug": "route-maps",
        "description": "Route-Map 정책 설정 파싱",
        "match_config": "route-map",
        "config_ordered": False,
    },
    {
        "name": "Policy-Based Routing (PBR)",
        "slug": "policy-based-routing",
        "description": "PBR 정책 기반 라우팅 설정 파싱",
        "match_config": "ip policy",
        "config_ordered": False,
    },
]


def api_get(endpoint, params=None):
    res = requests.get(f"{BASE_URL}/{endpoint.lstrip('/')}", headers=HEADERS, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


def api_post(endpoint, data):
    res = requests.post(f"{BASE_URL}/{endpoint.lstrip('/')}", headers=HEADERS, json=data, timeout=10)
    if not res.ok:
        raise RuntimeError(f"POST {endpoint} 실패 [{res.status_code}]: {res.text}")
    return res.json()


def api_patch(endpoint, data):
    res = requests.patch(f"{BASE_URL}/{endpoint.lstrip('/')}", headers=HEADERS, json=data, timeout=10)
    if not res.ok:
        raise RuntimeError(f"PATCH {endpoint} 실패 [{res.status_code}]: {res.text}")
    return res.json()


def setup_local_git_repo():
    """호스트에 로컬 bare Git 저장소 확인 및 생성"""
    repo_dir = "/root/nautobot-docker/git_repos/cisco-backup.git"
    print("[1/5] 로컬 Git 저장소 준비", flush=True)
    if not os.path.exists(repo_dir):
        print(f"  + 로컬 Git 저장소 생성: {repo_dir}", flush=True)
        os.makedirs("/root/nautobot-docker/git_repos", exist_ok=True)
        cmd = """
        TEMP_DIR=$(mktemp -d)
        cd $TEMP_DIR
        git init -b main
        git config user.name "Nautobot"
        git config user.email "nautobot@local"
        echo "# Cisco Config Backups" > README.md
        git add README.md
        git commit -m "Initial commit"
        git clone --bare . /root/nautobot-docker/git_repos/cisco-backup.git
        rm -rf $TEMP_DIR
        chmod -R 777 /root/nautobot-docker/git_repos
        """
        subprocess.run(cmd, shell=True, check=True)
    else:
        print(f"  - [기존 존재] 로컬 Git 저장소: {repo_dir}", flush=True)
        subprocess.run("chmod -R 777 /root/nautobot-docker/git_repos", shell=True, check=True)

    # Nautobot 컨테이너 내부 safe.directory 설정 확인
    subprocess.run("docker compose exec -T nautobot git config --global --add safe.directory '*'", shell=True, check=False)
    subprocess.run("docker compose exec -T nautobot-worker git config --global --add safe.directory '*'", shell=True, check=False)


def register_git_repository():
    """Nautobot에 로컬 Git 저장소 등록 및 동기화"""
    print("\n[2/5] Nautobot Git Repository 등록 및 동기화", flush=True)
    repos = api_get("extras/git-repositories/", params={"name": "local-cisco-backup"})["results"]
    if repos:
        repo_id = repos[0]["id"]
        print(f"  - [기존 존재] Git Repository: local-cisco-backup (ID: {repo_id})", flush=True)
    else:
        # Django ORM을 통해 file:// URL 등록
        cmd = """docker compose exec -T nautobot nautobot-server nbshell --command "
from nautobot.extras.models.datasources import GitRepository
repo, created = GitRepository.objects.get_or_create(
    name='local-cisco-backup',
    defaults={
        'remote_url': 'file:///opt/nautobot/git_repos/cisco-backup.git',
        'branch': 'main',
        'provided_contents': ['nautobot_golden_config.backupconfigs']
    }
)
" """
        subprocess.run(cmd, shell=True, check=True)
        repos = api_get("extras/git-repositories/", params={"name": "local-cisco-backup"})["results"]
        repo_id = repos[0]["id"]
        print(f"  + [신규 등록] Git Repository: local-cisco-backup (ID: {repo_id})", flush=True)

    # Git 저장소 동기화(Sync) 트리거
    sync_res = api_post(f"extras/git-repositories/{repo_id}/sync/", {})
    print(f"  ↳ Git 저장소 동기화 요청 완료: {sync_res.get('message')}", flush=True)
    return repo_id


def configure_golden_settings(repo_id):
    """Golden Config Settings에 백업 저장소 및 백업 경로 템플릿 설정"""
    print("\n[3/5] Golden Config 기본 설정(Settings) 업데이트", flush=True)

    # GraphQL Query 확인 또는 생성 (Golden Config SoT Aggregation 필수 요구사항)
    gql_list = api_get("extras/graphql-queries/", params={"name": "GS-Device-Query"})["results"]
    if gql_list:
        gql_id = gql_list[0]["id"]
    else:
        new_gql = api_post("extras/graphql-queries/", {
            "name": "GS-Device-Query",
            "query": "query ($device_id: ID!) { device(id: $device_id) { name } }"
        })
        gql_id = new_gql["id"]

    settings_list = api_get("plugins/golden-config/golden-config-settings/")["results"]
    if not settings_list:
        raise RuntimeError("Golden Config Default Settings가 존재하지 않습니다.")

    default_setting = settings_list[0]
    setting_id = default_setting["id"]

    # 백업 경로: {{ obj.location.name }}/{{ obj.name }}.cfg (예: Seoul-Lab/r1.cfg)
    payload = {
        "backup_repository": repo_id,
        "backup_path_template": "{{ obj.location.name }}/{{ obj.name }}.cfg",
        "backup_test_connectivity": False,  # 테스트 장비 환경에 맞춰 유연하게 설정
        "sot_agg_query": gql_id,
    }
    api_patch(f"plugins/golden-config/golden-config-settings/{setting_id}/", payload)
    print(f"  + 백업 저장소 연동 완료: local-cisco-backup", flush=True)
    print(f"  + 백업 경로 템플릿: {{{{ obj.location.name }}}}/{{{{ obj.name }}}}.cfg", flush=True)


def setup_compliance_rules():
    """라우팅, 인터페이스, ACL, Route-Map, PBR 파싱 규칙 등록"""
    print("\n[4/5] 설정 파싱(Compliance) 기능 및 규칙 생성", flush=True)
    platforms = api_get("dcim/platforms/", params={"name": "cisco_ios"})["results"]
    if not platforms:
        raise RuntimeError("cisco_ios 플랫폼을 찾을 수 없습니다.")
    platform_id = platforms[0]["id"]

    for rule_def in COMPLIANCE_RULES:
        feat_name = rule_def["name"]
        slug = rule_def["slug"]

        # Feature 확인 또는 생성
        feats = api_get("plugins/golden-config/compliance-feature/", params={"slug": slug})["results"]
        if feats:
            feat_id = feats[0]["id"]
            print(f"  - [기존 Feature] {feat_name}", flush=True)
        else:
            new_feat = api_post("plugins/golden-config/compliance-feature/", {
                "name": feat_name,
                "slug": slug,
                "description": rule_def["description"],
            })
            feat_id = new_feat["id"]
            print(f"  + [신규 Feature] {feat_name}", flush=True)

        # Rule 확인 또는 생성
        rules = api_get("plugins/golden-config/compliance-rule/", params={"feature": feat_id, "platform": platform_id})["results"]
        if rules:
            print(f"    ↳ [기존 Rule] match_config: \"{rule_def['match_config']}\"", flush=True)
        else:
            api_post("plugins/golden-config/compliance-rule/", {
                "feature": feat_id,
                "platform": platform_id,
                "description": f"{feat_name} 파싱 규칙",
                "match_config": rule_def["match_config"],
                "config_type": "cli",
                "config_ordered": rule_def["config_ordered"],
            })
            print(f"    ↳ [신규 Rule] match_config: \"{rule_def['match_config']}\" (ordered={rule_def['config_ordered']})", flush=True)


def setup_jobs_and_schedule():
    """백업 및 파싱 Job 활성화 & 30분 주기 스케줄링 등록"""
    print("\n[5/5] 백업 및 파싱 Job 활성화 & 30분 자동 스케줄 등록", flush=True)

    # 1. Job 모델 활성화 (Backup Configurations & Perform Configuration Compliance)
    backup_job = api_get("extras/jobs/", params={"name": "Backup Configurations"})["results"][0]
    compliance_job = api_get("extras/jobs/", params={"name": "Perform Configuration Compliance"})["results"][0]

    api_patch(f"extras/jobs/{backup_job['id']}/", {"enabled": True})
    api_patch(f"extras/jobs/{compliance_job['id']}/", {"enabled": True})
    print(f"  + Job 활성화 완료: Backup Configurations, Perform Configuration Compliance", flush=True)

    # 2. Celery Beat Crontab 30분 주기 스케줄 등록 (Django Celery Beat)
    cmd = f"""docker compose exec -T nautobot nautobot-server nbshell --command "
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from nautobot.extras.models.jobs import Job

# 30분마다 실행되는 크론탭 (*/30 * * * *)
crontab, _ = CrontabSchedule.objects.get_or_create(minute='*/30', hour='*', day_of_week='*', day_of_month='*', month_of_year='*')

# 백업 작업 스케줄링
job = Job.objects.get(name='Backup Configurations')
task, created = PeriodicTask.objects.get_or_create(
    name='30분 주기 Cisco 장비 백업 (Golden Config)',
    defaults={{
        'crontab': crontab,
        'task': 'nautobot.extras.jobs.scheduled_job_handler',
        'kwargs': '{{\"job_model_id\": \"{backup_job["id"]}\"}}',
        'enabled': True,
    }}
)
if not created:
    task.enabled = True
    task.crontab = crontab
    task.save()

print('Scheduled PeriodicTask:', task.name, 'Enabled:', task.enabled)
" """
    subprocess.run(cmd, shell=True, check=True)
    print("  + 30분 주기 자동 백업 등록 완료 (crontab: */30 * * * *)", flush=True)


def main():
    print("=== Nautobot Golden Config 환경 설정 시작 ===")
    setup_local_git_repo()
    repo_id = register_git_repository()
    configure_golden_settings(repo_id)
    setup_compliance_rules()
    setup_jobs_and_schedule()
    print("\n=== 모든 설정이 완료되었습니다! ===")
    print("1. 백업 파일 저장 위치: /root/nautobot-docker/git_repos/cisco-backup.git")
    print("2. 자동 백업 주기: 매 30분마다 자동 실행")
    print("3. 매뉴얼 백업 실행: Jobs > Installed Jobs > Backup Configurations > Run Job Now")


if __name__ == "__main__":
    main()
