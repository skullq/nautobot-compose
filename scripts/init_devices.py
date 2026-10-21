#!/usr/bin/env python3
"""
Nautobot 초기 선행 데이터 및 장비 일괄 등록 자동화 스크립트
- 선행 필수 객체(LocationType, Location, Manufacturer, Platform, DeviceType, Role, Prefix) 자동 확인 및 생성
- 장비(Device), 인터페이스(Interface), 관리 IP(IPAddress) 및 매핑(IPAddressToInterface), Primary IP 자동 연동
"""

import os
import sys
import argparse
import yaml
import requests

DEFAULT_URL = os.environ.get("NAUTOBOT_URL", "http://127.0.0.1:8888/api")
DEFAULT_TOKEN = os.environ.get("NAUTOBOT_TOKEN", "0123456789abcdef0123456789abcdef01234567")


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

    def patch(self, endpoint, data):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        res = self.session.patch(url, json=data, timeout=10)
        if not res.ok:
            raise RuntimeError(f"PATCH {url} failed [{res.status_code}]: {res.text}")
        return res.json()

    def get_or_create(self, endpoint, query_params, create_payload, name_field="name"):
        res = self.get(endpoint, params=query_params)
        results = res.get("results", [])
        if results:
            print(f"  - [기존 존재] {endpoint}: {results[0].get(name_field) or results[0].get('model') or results[0].get('prefix')}", flush=True)
            return results[0]
        created = self.post(endpoint, create_payload)
        print(f"  + [신규 생성] {endpoint}: {created.get(name_field) or created.get('model') or created.get('prefix')}", flush=True)
        return created


def load_yaml(filepath):
    if not os.path.exists(filepath):
        print(f"오류: 설정 파일({filepath})을 찾을 수 없습니다.", file=sys.stderr, flush=True)
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Nautobot 선행 데이터 및 장비 일괄 등록 스크립트")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Nautobot API URL (기본값: {DEFAULT_URL})")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Nautobot API 토큰")
    parser.add_argument("--file", default=os.path.join(os.path.dirname(__file__), "devices.yaml"), help="장비 정의 YAML 파일 경로")
    args = parser.parse_args()

    print(f"=== Nautobot 인벤토리 동기화 시작 ===", flush=True)
    print(f"Target URL: {args.url}", flush=True)
    print(f"Data File : {args.file}\n", flush=True)

    client = NautobotClient(args.url, args.token)
    data = load_yaml(args.file)

    # 공통 Status(Active) 및 Namespace(Global) ID 조회
    status_active = client.get("extras/statuses/", params={"name": "Active"})["results"][0]["id"]
    namespaces = client.get("ipam/namespaces/", params={"name": "Global"})["results"]
    namespace_global = namespaces[0]["id"] if namespaces else None

    # 1. Location Types
    print("[1/8] Location Types 확인 및 생성", flush=True)
    location_types = {}
    for item in data.get("location_types", []):
        name = item["name"]
        payload = {
            "name": name,
            "content_types": item.get("content_types", ["dcim.device"])
        }
        lt = client.get_or_create("dcim/location-types/", {"name": name}, payload)
        location_types[name] = lt["id"]

    # 2. Locations
    print("\n[2/8] Locations 확인 및 생성", flush=True)
    locations = {}
    for item in data.get("locations", []):
        name = item["name"]
        lt_name = item["location_type"]
        payload = {
            "name": name,
            "location_type": location_types[lt_name],
            "status": status_active,
        }
        loc = client.get_or_create("dcim/locations/", {"name": name}, payload)
        locations[name] = loc["id"]

    # 3. Manufacturers
    print("\n[3/8] Manufacturers 확인 및 생성", flush=True)
    manufacturers = {}
    for item in data.get("manufacturers", []):
        name = item["name"]
        mfg = client.get_or_create("dcim/manufacturers/", {"name": name}, {"name": name})
        manufacturers[name] = mfg["id"]

    # 4. Platforms
    print("\n[4/8] Platforms 확인 및 생성", flush=True)
    platforms = {}
    for item in data.get("platforms", []):
        name = item["name"]
        mfg_name = item.get("manufacturer")
        payload = {
            "name": name,
            "network_driver": item.get("network_driver", name),
        }
        if mfg_name and mfg_name in manufacturers:
            payload["manufacturer"] = manufacturers[mfg_name]
        plat = client.get_or_create("dcim/platforms/", {"name": name}, payload)
        platforms[name] = plat["id"]

    # 5. Device Types
    print("\n[5/8] Device Types 확인 및 생성", flush=True)
    device_types = {}
    for item in data.get("device_types", []):
        model = item["model"]
        mfg_name = item["manufacturer"]
        payload = {
            "model": model,
            "manufacturer": manufacturers[mfg_name],
        }
        dt = client.get_or_create("dcim/device-types/", {"model": model}, payload, name_field="model")
        device_types[model] = dt["id"]

    # 6. Roles
    print("\n[6/8] Roles 확인 및 생성", flush=True)
    roles = {}
    for item in data.get("roles", []):
        name = item["name"]
        payload = {
            "name": name,
            "color": item.get("color", "9e9e9e"),
            "content_types": item.get("content_types", ["dcim.device"]),
        }
        r = client.get_or_create("extras/roles/", {"name": name}, payload)
        roles[name] = r["id"]

    # 7. Prefixes (IPAM)
    print("\n[7/8] Prefixes 확인 및 생성", flush=True)
    for item in data.get("prefixes", []):
        prefix_str = item["prefix"]
        ns_name = item.get("namespace", "Global")
        ns_id = namespace_global
        if ns_name != "Global":
            ns_res = client.get("ipam/namespaces/", params={"name": ns_name})["results"]
            ns_id = ns_res[0]["id"] if ns_res else namespace_global

        payload = {
            "prefix": prefix_str,
            "namespace": ns_id,
            "status": status_active,
            "type": item.get("type", "network"),
        }
        client.get_or_create("ipam/prefixes/", {"prefix": prefix_str, "namespace": ns_id}, payload, name_field="prefix")

    # 8. Devices (장비 대량 생성)
    print("\n[8/8] Devices 및 관리 IP 일괄 동기화", flush=True)
    created_count = 0
    skipped_count = 0

    for dev in data.get("devices", []):
        dev_name = dev["name"]
        existing = client.get("dcim/devices/", params={"name": dev_name})["results"]
        if existing:
            device_id = existing[0]["id"]
            # 기존 장비의 모델, 역할, 플랫폼 등이 변경되었는지 확인 및 갱신
            update_payload = {}
            current_dt_id = existing[0].get("device_type", {}).get("id")
            target_dt_id = device_types[dev["device_type"]]
            if current_dt_id != target_dt_id:
                update_payload["device_type"] = target_dt_id

            current_role_id = existing[0].get("role", {}).get("id")
            target_role_id = roles[dev["role"]]
            if current_role_id != target_role_id:
                update_payload["role"] = target_role_id

            if dev.get("platform") and dev["platform"] in platforms:
                current_plat_id = existing[0].get("platform", {}).get("id")
                target_plat_id = platforms[dev["platform"]]
                if current_plat_id != target_plat_id:
                    update_payload["platform"] = target_plat_id

            if update_payload:
                client.patch(f"dcim/devices/{device_id}/", update_payload)
                print(f"  * [정보 갱신] Device: {dev_name} (Model: {dev['device_type']}, Role: {dev['role']})", flush=True)
            else:
                print(f"  - [기존 존재] Device: {dev_name}", flush=True)
            skipped_count += 1
        else:
            payload = {
                "name": dev_name,
                "role": roles[dev["role"]],
                "device_type": device_types[dev["device_type"]],
                "location": locations[dev["location"]],
                "status": status_active,
            }
            if dev.get("platform") and dev["platform"] in platforms:
                payload["platform"] = platforms[dev["platform"]]

            created_dev = client.post("dcim/devices/", payload)
            device_id = created_dev["id"]
            created_count += 1
            print(f"  + [신규 생성] Device: {dev_name} (Role: {dev['role']}, Model: {dev['device_type']})", flush=True)

        # 인터페이스 및 관리 IP 할당
        if dev.get("management_ip") and dev.get("interface_name"):
            if_name = dev["interface_name"]
            mgmt_ip = dev["management_ip"]

            # 8-1. 인터페이스 확인/생성
            if_list = client.get("dcim/interfaces/", params={"device_id": device_id, "name": if_name})["results"]
            if if_list:
                interface_id = if_list[0]["id"]
            else:
                new_if = client.post("dcim/interfaces/", {
                    "device": device_id,
                    "name": if_name,
                    "type": "other",
                    "status": status_active,
                    "mgmt_only": True,
                })
                interface_id = new_if["id"]

            # 8-2. IP 주소 확인/생성
            ip_list = client.get("ipam/ip-addresses/", params={"address": mgmt_ip})["results"]
            if ip_list:
                ip_id = ip_list[0]["id"]
            else:
                new_ip = client.post("ipam/ip-addresses/", {
                    "address": mgmt_ip,
                    "status": status_active,
                    "namespace": namespace_global,
                })
                ip_id = new_ip["id"]

            # 8-3. IPAddressToInterface 연결 확인/생성
            map_list = client.get("ipam/ip-address-to-interface/", params={"ip_address": ip_id, "interface": interface_id})["results"]
            if not map_list:
                client.post("ipam/ip-address-to-interface/", {
                    "ip_address": ip_id,
                    "interface": interface_id,
                })

            # 8-4. 장비의 Primary IP4 지정
            client.patch(f"dcim/devices/{device_id}/", {"primary_ip4": ip_id})
            print(f"    ↳ Primary IP 설정 완료: {dev_name} [{if_name}] -> {mgmt_ip}", flush=True)

    print(f"\n=== 인벤토리 동기화 완료 ===", flush=True)
    print(f"신규 생성된 장비: {created_count}대")
    print(f"기존 유지된 장비: {skipped_count}대", flush=True)


if __name__ == "__main__":
    main()
