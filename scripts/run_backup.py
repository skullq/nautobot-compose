#!/usr/bin/env python3
"""
Nautobot Golden Configuration 수동(매뉴얼) 백업 및 컴플라이언스(파싱) 실행 스크립트
- Backup Configurations Job을 즉시 큐에 추가하여 r1~r5의 running-config 수집
- 필요에 따라 Perform Configuration Compliance Job을 연속 실행하여 파싱 분석 수행
"""

import os
import sys
import argparse
import requests

BASE_URL = os.environ.get("NAUTOBOT_URL", "http://127.0.0.1:8888/api").rstrip("/")
TOKEN = os.environ.get("NAUTOBOT_TOKEN", "0123456789abcdef0123456789abcdef01234567")
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def trigger_job(job_name, extra_data=None):
    # Job ID 조회
    res = requests.get(f"{BASE_URL}/extras/jobs/", headers=HEADERS, params={"name": job_name}, timeout=10)
    res.raise_for_status()
    results = res.json().get("results", [])
    if not results:
        print(f"오류: Job '{job_name}'을 찾을 수 없습니다.", file=sys.stderr)
        return None

    job_id = results[0]["id"]

    # Job 실행 트리거
    payload = {"data": extra_data or {}}
    run_res = requests.post(f"{BASE_URL}/extras/jobs/{job_id}/run/", headers=HEADERS, json=payload, timeout=10)
    if not run_res.ok:
        print(f"오류: Job 실행 실패 [{run_res.status_code}]: {run_res.text}", file=sys.stderr)
        return None

    data = run_res.json()
    job_result = data.get("job_result", {})
    return job_result


def main():
    parser = argparse.ArgumentParser(description="Nautobot Golden Config 수동 백업 및 파싱 실행기")
    parser.add_argument("--compliance", action="store_true", help="백업과 함께 파싱(컴플라이언스) 검증 Job도 실행")
    args = parser.parse_args()

    print("=== [Golden Config] 수동 백업 요청 ===", flush=True)
    backup_result = trigger_job("Backup Configurations")
    if backup_result:
        print(f"✔ 백업 작업이 정상적으로 등록되었습니다.")
        print(f"  - Job Result ID : {backup_result.get('id')}")
        print(f"  - Web UI 확인   : http://localhost:8888/extras/job-results/{backup_result.get('id')}/")
        print(f"  - 로컬 파일 저장 : /root/nautobot-docker/git_repos/cisco-backup.git\n")

    if args.compliance:
        print("=== [Golden Config] 파싱 및 컴플라이언스 분석 요청 ===", flush=True)
        comp_result = trigger_job("Perform Configuration Compliance")
        if comp_result:
            print(f"✔ 컴플라이언스 분석 작업이 등록되었습니다.")
            print(f"  - Job Result ID : {comp_result.get('id')}")
            print(f"  - Web UI 확인   : http://localhost:8888/extras/job-results/{comp_result.get('id')}/\n")


if __name__ == "__main__":
    main()
