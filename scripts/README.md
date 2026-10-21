# Nautobot Cisco Golden Config 가이드

Cisco 장비(`r1` ~ `r5`)를 대상으로 **로컬 Git 저장소 백업**, **30분 주기 자동 백업 & 매뉴얼 백업**, 그리고 **상세 네트워크 설정 파싱(컴플라이언스 분석)**을 지원하는 통합 환경입니다.

---

## 1. 구성 파일 안내
* `setup_golden_config.py`: 로컬 Git 저장소 생성, 파싱 규칙 9종 등록, 30분 주기 스케줄링을 한 번에 설정하는 자동화 스크립트
* `run_backup.py`: 수동(매뉴얼) 백업 및 파싱을 즉시 실행하는 CLI 도구
* `init_devices.py`: 장비(r1~r5) 및 선행 데이터 일괄 등록 스크립트
* `init_cables.py`: 장비 간 인터페이스 및 케이블(Cable) 연결 일괄 등록 스크립트 (Topology View 연동)
* `devices.yaml`: 장비 인벤토리 정의 파일

---

## 2. 파싱 및 컴플라이언스 분석 항목 (9개 영역)

장비의 `running-config` 백업 완료 후 다음 9가지 핵심 설정 블록이 자동으로 추출·파싱됩니다.

| No | 기능 분류 (Feature) | 매칭 설정 (Match Config) | 파싱 내용 |
| :---: | :--- | :--- | :--- |
| **1** | **Interfaces** | `interface` | 물리 포트, Loopback, 서브인터페이스, IP 주소 설정 블록 |
| **2** | **Static Routing** | `ip route` | 정적 IPv4/IPv6 라우팅 경로 |
| **3** | **BGP Routing** | `router bgp` | AS 번호, Neighbor, Address-Family, 피어링 설정 |
| **4** | **OSPF Routing** | `router ospf` | Process ID, Network/Area, OSPF 인터페이스 설정 |
| **5** | **EIGRP Routing** | `router eigrp` | AS 번호, Network 대역 설정 |
| **6** | **IS-IS Routing** | `router isis` | IS-IS 라우팅 프로세스 및 NET 설정 |
| **7** | **Access-Lists** | `ip access-list` | 표준/확장 ACL 규칙 (순서 보장 검증) |
| **8** | **Route-Maps** | `route-map` | 라우트맵 정책, Match 및 Set 조건 |
| **9** | **Policy-Based Routing (PBR)** | `ip policy` | 인터페이스 PBR 적용 및 Local PBR 설정 |

---

## 3. 백업 운영 방법

### A. 30분 주기 자동 백업 (Scheduled Job)
* **주기**: 매 30분마다 자동 실행 (`crontab: */30 * * * *`)
* Celery Beat 스케줄러가 백그라운드에서 주기적으로 `Backup Configurations` 잡을 실행하여 최신 설정을 로컬 Git 저장소에 커밋합니다.

### B. 수동(매뉴얼) 백업 실행
원할 때 언제든지 즉시 백업할 수 있습니다.

#### 터미널 CLI 실행
```bash
# 즉시 백업 실행
python3 scripts/run_backup.py

# 백업 후 파싱(컴플라이언스)까지 연속 실행
python3 scripts/run_backup.py --compliance
```

#### Web UI 실행
1. 웹 브라우저에서 `http://localhost:8888` 접속
2. **Jobs** > **Installed Jobs** 이동
3. **Backup Configurations** 항목 우측의 **▶ Run** 버튼 클릭 후 실행

---

## 4. 백업 파일 저장 위치 및 확인

백업된 모든 Cisco 설정 파일은 호스트 머신의 아래 디렉토리에 버전 관리됩니다.

```bash
# 호스트 로컬 Git 저장소 위치
/root/nautobot-docker/git_repos/cisco-backup.git

# 백업 파일 저장 형식 (Location/Device.cfg)
Seoul-Lab/r1.cfg
Seoul-Lab/r2.cfg
Seoul-Lab/r3.cfg
Seoul-Lab/r4.cfg
Seoul-Lab/r5.cfg
```

---

## 5. 파싱 결과 확인 (Web UI)
* 백업 및 파싱이 완료되면 **Golden Configuration** > **Compliance** > **Overview** 화면에서 각 장비(`r1` ~ `r5`)별로 상기 9가지 설정 항목이 어떻게 파싱되었는지 실시간 매트릭스로 확인하실 수 있습니다.
