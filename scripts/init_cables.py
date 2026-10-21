#!/usr/bin/env python3
"""
Nautobot 장비 간 인터페이스 및 케이블(Cable) 일괄 연동 스크립트
- Containerlab(iol-lab1)의 실제 연결 구성을 Nautobot DCIM Interface 및 Cable 객체로 자동 등록합니다.
"""

import os
import sys
import requests

DEFAULT_URL = os.environ.get("NAUTOBOT_URL", "http://127.0.0.1:8888/api")
DEFAULT_TOKEN = os.environ.get("NAUTOBOT_TOKEN", "0123456789abcdef0123456789abcdef01234567")

# 실제 Containerlab iol-lab1 토폴로지 링크 구성
LINKS = [
    {"src": ("r1", "Ethernet0/1"), "dst": ("r4", "Ethernet0/1")},
    {"src": ("r2", "Ethernet0/1"), "dst": ("r4", "Ethernet0/2")},
    {"src": ("r3", "Ethernet0/1"), "dst": ("r4", "Ethernet0/3")},
    {"src": ("r1", "Ethernet0/2"), "dst": ("r5", "Ethernet0/1")},
    {"src": ("r2", "Ethernet0/2"), "dst": ("r5", "Ethernet0/2")},
    {"src": ("r3", "Ethernet0/2"), "dst": ("r5", "Ethernet0/3")},
]


class NautobotClient:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def get(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        res = self.session.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def post(self, endpoint, data):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        res = self.session.post(url, json=data, timeout=10)
        if not res.ok:
            raise RuntimeError(f"POST {url} failed [{res.status_code}]: {res.text}")
        return res.json()


def main():
    print("=== Nautobot 토폴로지 케이블(Cable) 등록 시작 ===")
    client = NautobotClient(DEFAULT_URL, DEFAULT_TOKEN)

    # 1. 상태(Status) ID 조회
    status_active = client.get("extras/statuses/", params={"name": "Active"})["results"][0]["id"]
    status_connected = client.get("extras/statuses/", params={"name": "Connected"})["results"][0]["id"]

    # 2. 장비(Device) ID 조회
    devices_res = client.get("dcim/devices/")["results"]
    device_map = {d["name"]: d["id"] for d in devices_res}

    # 3. 인터페이스 조회 및 생성
    def get_or_create_interface(device_name, intf_name):
        dev_id = device_map[device_name]
        existing = client.get("dcim/interfaces/", params={"device_id": dev_id, "name": intf_name})["results"]
        if existing:
            return existing[0]["id"]
        payload = {
            "device": dev_id,
            "name": intf_name,
            "type": "1000base-t",
            "status": status_active,
        }
        res = client.post("dcim/interfaces/", payload)
        print(f"  + 인터페이스 생성: {device_name} {intf_name}")
        return res["id"]

    # 4. 케이블 연결
    print("\n[인터페이스 및 케이블 연결 등록]")
    for link in LINKS:
        src_dev, src_intf = link["src"]
        dst_dev, dst_intf = link["dst"]

        if src_dev not in device_map or dst_dev not in device_map:
            print(f"  - 건너뜀: {src_dev} 또는 {dst_dev} 장비가 존재하지 않음")
            continue

        src_intf_id = get_or_create_interface(src_dev, src_intf)
        dst_intf_id = get_or_create_interface(dst_dev, dst_intf)

        # 이미 케이블이 연결되어 있는지 확인
        cables = client.get("dcim/cables/")["results"]
        already_connected = False
        for c in cables:
            term_ids = [c.get("termination_a_id"), c.get("termination_b_id")]
            if src_intf_id in term_ids and dst_intf_id in term_ids:
                already_connected = True
                break

        if already_connected:
            print(f"  - [이미 연결됨] {src_dev} {src_intf} <--> {dst_dev} {dst_intf}")
            continue

        cable_payload = {
            "status": status_connected,
            "termination_a_type": "dcim.interface",
            "termination_a_id": src_intf_id,
            "termination_b_type": "dcim.interface",
            "termination_b_id": dst_intf_id,
            "type": "cat6",
        }
        try:
            client.post("dcim/cables/", cable_payload)
            print(f"  + [케이블 연결 생성] {src_dev} {src_intf} <---> {dst_dev} {dst_intf}")
        except Exception as e:
            print(f"  ! 케이블 연결 실패 ({src_dev}-{dst_dev}): {e}")

    print("\n=== 모든 케이블 등록 완료 ===")


if __name__ == "__main__":
    main()
