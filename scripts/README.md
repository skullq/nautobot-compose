# Nautobot Cisco 장비 일괄 등록 및 Golden Config 연동 가이드

Cisco 장비 전용으로 **Golden Config가 SSH 접속하여 전체 설정과 IP를 수집하는 데 필요한 최소 필수 데이터**를 자동 등록하는 도구입니다.

---

## 1. Golden Config 수집 원리 및 최소 등록 조건

Golden Config는 Nornir/Netmiko 라이브러리를 통해 장비에 직접 SSH로 접근하여 `show running-config` 및 IP/인터페이스 상태를 파싱해 옵니다.  
따라서 Nautobot에는 장비의 모든 상세 인터페이스나 IP를 미리 등록할 필요가 없으며, **SSH 접속에 필요한 최소 3가지 정보**만 등록되어 있으면 충분합니다.

1. **접속 IP (Primary IP)**: 장비에 SSH 접근할 관리 IP 주소
2. **Platform (`cisco_ios` / `cisco_xe`)**: Nornir가 사용할 Cisco 접속 드라이버 식별자
3. **Status (`Active`)**: Golden Config Job의 수집 대상 필터링 조건

> 장비 등록 후 Golden Config 백업 Job이 실행되면, 장비 내부의 모든 인터페이스(Loopback, VLAN, 물리 포트 등)와 세부 설정이 Nautobot 및 Git 저장소로 자동 동기화됩니다.

---

## 2. 구성 파일
* `devices.yaml`: Cisco 전용 선행 데이터(제조사, 모델, 플랫폼, 접속 대역) 및 장비 목록 정의
* `init_devices.py`: Nautobot REST API를 통해 데이터를 멱등하게 일괄 생성하는 스크립트

---

## 3. 실행 방법

Nautobot이 구동 중인 상태에서 터미널에서 실행합니다.

```bash
python3 scripts/init_devices.py
```

### 실제 장비 정보로 변경하는 방법
[scripts/devices.yaml](file:///root/nautobot-docker/scripts/devices.yaml) 파일의 `devices` 항목에서 실제 환경에 맞게 IP와 장비명만 수정하시면 됩니다.

```yaml
devices:
  - name: "cisco-rtr-01"                  # 장비 호스트명
    role: "Router"                        # 역할 (Router 또는 Switch)
    device_type: "C8000V"                 # 모델 (C8000V, CSR1000V, Catalyst-9300 등)
    location: "Seoul-Lab"                 # 위치
    platform: "cisco_ios"                 # Cisco 접속 드라이버
    status: "Active"
    management_ip: "192.168.100.11/24"   # 실제 장비 SSH 접속 IP
    interface_name: "GigabitEthernet1"    # 관리 인터페이스명
```

---

## 4. 등록 후 Golden Config 연동 체크포인트
장비 등록 후 Nautobot 웹 UI에서 다음 사항을 연동합니다.

1. **Secrets / Secret Groups** (*Extensibility > Secret Groups*):
   * Cisco 장비에 SSH 접속할 계정/비밀번호(ID/PW 또는 Enable Secret)를 등록하고 장비에 연결합니다.
2. **Golden Config Scope**:
   * Golden Config의 Dynamic Group에서 `Platform = cisco_ios` 및 `Status = Active`인 장비를 타겟으로 지정합니다.
3. **Backup Job 실행**:
   * *Jobs > Golden Configuration > Backup* 실행 시 등록된 Primary IP로 자동 접속하여 전체 설정을 백업합니다.
