# Nautobot Docker 가이드

로컬 환경에서 네트워크 자동화 및 SoT(Source of Truth) 테스트를 위한 Docker Compose 기반 Nautobot 3.1 배포 가이드입니다.  
**Golden Config**, **Nornir**, **Topology Views**, **SSoT** 플러그인이 기본 포함되어 구성되어 있으며, 필요에 따라 추가 앱(플러그인)을 설치하고 설정할 수 있습니다.  

> **주의**: 보안을 고려하지 않은 구성이므로 외부 공개 없이 로컬 환경에서만 사용하세요.

---

## 목차
1. [기본 접속 정보](#기본-접속-정보)
2. [주요 탑재 플러그인 & 활용](#주요-탑재-플러그인--활용)
   - [Golden Config (형상 관리 & 백업)](#1-golden-config-설정-형상-관리--백업)
   - [Topology Views (네트워크 토폴로지 시각화)](#2-topology-views-네트워크-토폴로지-시각화)
   - [SSoT (데이터 동기화 & 통합)](#3-ssot-single-source-of-truth-데이터-동기화)
3. [초기 실행 (Quick Start)](#초기-실행-quick-start)
4. [장비 및 초기 데이터 일괄 등록](#장비-및-초기-데이터-일괄-등록)
5. [신규 앱(플러그인) 추가](#신규-앱플러그인-추가)
6. [앱 옵션 변경](#앱-옵션-변경)
7. [운영 명령어](#운영-명령어)

---

## 기본 접속 정보

| 항목 | 내용 |
| :--- | :--- |
| **Web UI** | `http://localhost:8888` |
| **계정** | ID: `admin` / PW: `admin` |
| **API Token** | `0123456789abcdef0123456789abcdef01234567` |
| **토폴로지 뷰** | `http://localhost:8888/plugins/topology-views/topology/` (상단 메뉴 `Plugins` → `Topology Views`) |
| **SSoT 대시보드** | `http://localhost:8888/plugins/ssot/` (상단 메뉴 `SSoT` 또는 `Plugins` → `SSoT`) |
| **구성 컨테이너** | Nautobot Web, Celery Worker, Celery Beat, PostgreSQL 15, Redis 7 |
| **탑재 플러그인** | `nautobot-golden-config`, `nautobot-plugin-nornir`, `nautobot-topology-views`, `nautobot-ssot` |

---

## 주요 탑재 플러그인 & 활용

### 1. Golden Config (설정 형상 관리 & 백업)
- **개요**: 네트워크 장비의 실제 CLI 구성을 자동으로 백업하고, SoT 표준 형상(Intended)과 비교 분석하는 자동화 앱입니다.
- **주요 기능**:
  - **자동 백업**: Celery Beat 스케줄러를 통한 30분 주기 자동 백업
  - **수동 백업**: `python3 scripts/run_backup.py` 실행 또는 Web UI Jobs 메뉴에서 원클릭 백업 트리거
  - **로컬 Git 연동**: 백업된 장비 설정은 `./git_repos/golden_config/` 로컬 Git 리포지토리에 자동 커밋되어 안전하게 보관
  - **GraphQL 조회**: GraphQL API (`/api/graphql/`)를 통해 백업 이력 및 컴플라이언스 상태 쿼리 가능

### 2. Topology Views (네트워크 토폴로지 시각화)
- **개요**: Nautobot에 등록된 장비(Devices)와 인터페이스 간 연결(Cables) 데이터를 분석하여 인터랙티브한 네트워크 토폴로지 다이어그램을 시각화합니다.
- **접속 방법**:
  - 웹 브라우저에서 `http://localhost:8888/plugins/topology-views/topology/` 로 바로 이동
  - 또는 Nautobot 상단 네비게이션 바에서 **`Plugins`** → **`Topology Views`** 선택
- **주요 기능**:
  - **동적 필터링**: Location(사이트), 장비 역할(Role), 태그, 디바이스 타입 등으로 원하는 영역만 선택하여 다이어그램 생성
  - **좌표 드래그 및 저장**: 토폴로지 맵에서 노드를 드래그하여 배치한 뒤, 현재 레이아웃 좌표를 저장하여 다음에 동일한 형태로 유지 가능 (`allow_coordinates_saving: True`)
  - **장비 정보 팝업**: 노드를 클릭하면 IP 주소, 모델, 시리얼 번호 등의 상세 정보 확인
  - **인터페이스 연결 시각화**: 인터페이스 간 물리 케이블 연결 및 상태를 다이어그램에 선으로 표시
- **설정 옵션 (`nautobot_config.py`)**:
  ```python
  PLUGINS_CONFIG = {
      "nautobot_topology_views": {
          "allow_coordinates_saving": True,   # 사용자 정의 노드 배치 좌표 저장 허용
          "always_save_coordinates": False,   # 이동 즉시 자동 저장 여부 (선택)
      },
  }
  ```

### 3. SSoT (Single Source of Truth, 데이터 동기화)
- **개요**: 외부 IT 시스템(ServiceNow, Cisco ACI, Infoblox, IP Fabric 등) 또는 사용자 정의 데이터 소스와 Nautobot 간의 양방향 데이터 집계 및 동기화를 중계하는 핵심 프레임워크입니다 (`DiffSync` 엔진 기반).
- **접속 방법**:
  - 웹 브라우저에서 `http://localhost:8888/plugins/ssot/` 로 이동
  - 또는 상단 네비게이션 바의 **`SSoT`** 메뉴 (또는 **`Plugins`** → **`SSoT`**) 선택
- **주요 기능**:
  - **DiffSync 엔진**: 두 시스템 간 데이터의 생성(Create), 수정(Update), 삭제(Delete) 차이점을 계산하여 정확한 동기화 수행
  - **대시보드 & 잡 이력**: 동기화 이력, 변경 사항(Diff), 실행 상태 및 로그를 직관적인 대시보드에서 실시간 모니터링
  - **확장 통합(Integrations)**: 필요에 따라 ServiceNow, Infoblox, CloudVision, ACI 등의 공식 어댑터를 활성화하거나 직접 커스텀 DiffSync 동기화 Job 등록 가능
- **설정 옵션 (`nautobot_config.py`)**:
  ```python
  PLUGINS_CONFIG = {
      "nautobot_ssot": {
          "hide_example_jobs": False,  # SSoT 예제 동기화 잡 표시 여부
      },
  }
  ```

---

## 초기 실행 (Quick Start)

```bash
# 1. 설정 검증
docker compose config

# 2. 이미지 빌드
docker compose build --no-cache

# 3. DB 마이그레이션 및 정적 파일 수집
docker compose run --rm nautobot nautobot-server post_upgrade

# 4. 서비스 실행
docker compose up -d
```

### 정상 실행 확인 예시
```bash
skullq@containerlab:~/nautobot-docker# docker compose up -d
[+] up 6/6
 ✔ Network nautobot-docker_default                Created                                                   
 ✔ Container nautobot-docker-db-1                 Started                                                   
 ✔ Container nautobot-docker-redis-1              Started                                                   
 ✔ Container nautobot-docker-nautobot-worker-1    Started                                                   
 ✔ Container nautobot-docker-nautobot-1           Started                                                   
 ✔ Container nautobot-docker-nautobot-scheduler-1 Started

skullq@containerlab:~/nautobot-docker# docker ps -a
CONTAINER ID   IMAGE                                        COMMAND                  CREATED              STATUS                        PORTS                                                   NAMES
648b1a41a01f   nautobot-docker-nautobot-scheduler           "nautobot-server cel…"   About a minute ago   Up About a minute (healthy)   8080/tcp, 8443/tcp                                      nautobot-docker-nautobot-scheduler-1
97084d5c574f   nautobot-docker-nautobot                     "/docker-entrypoint.…"   About a minute ago   Up About a minute (healthy)   8443/tcp, 0.0.0.0:8888->8080/tcp, [::]:8888->8080/tcp   nautobot-docker-nautobot-1
2afd71d537aa   nautobot-docker-nautobot-worker              "nautobot-server cel…"   About a minute ago   Up About a minute (healthy)   8080/tcp, 8443/tcp                                      nautobot-docker-nautobot-worker-1
3ecde5994807   redis:7-alpine                               "docker-entrypoint.s…"   About a minute ago   Up About a minute             6379/tcp                                                nautobot-docker-redis-1
439e619c2937   postgres:15-alpine                           "docker-entrypoint.s…"   About a minute ago   Up About a minute             5432/tcp                                                nautobot-docker-db-1
```

실행 후 웹 브라우저에서 `http://localhost:8888`로 접속합니다.

---

## 장비 및 초기 데이터 일괄 등록

테스트를 위한 선행 데이터(위치, 제조사, 장비 모델, 역할, IP 대역)와 장비 목록, 그리고 장비 간 케이블 연결을 자동 생성하려면 아래 스크립트를 순서대로 실행합니다.

```bash
# 1. 선행 필수 데이터 및 대상 장비(r1 ~ r5) 일괄 등록
python3 scripts/init_devices.py

# 2. 장비 간 인터페이스 및 케이블(Cable) 연결 등록 (Topology View 시각화용)
python3 scripts/init_cables.py
```
> 등록할 장비 목록이나 IP 대역은 [scripts/devices.yaml](file:///root/nautobot-docker/scripts/devices.yaml)에서 수정할 수 있습니다. 자세한 내용은 [scripts/README.md](file:///root/nautobot-docker/scripts/README.md)를 참고하세요.

---

## 신규 앱(플러그인) 추가

새로운 Nautobot 앱을 설치할 때는 다음 3단계를 진행합니다.

### 1. Dockerfile 수정
설치할 패키지를 `pip install` 목록에 추가합니다. (OS 라이브러리가 필요하면 `apt-get`에 추가)

```dockerfile
# Dockerfile
RUN pip install --no-cache-dir \
    "scrapli<2026" \
    nautobot-plugin-nornir \
    nautobot-golden-config \
    "nautobot-topology-views==4.5.1.1" \
    "nautobot-ssot==4.7.0" \
    nautobot-device-lifecycle-mgmt  # 추가할 신규 패키지명 (하이픈 사용)
```

### 2. nautobot_config.py 등록
앱 모듈명을 `PLUGINS` 및 `PLUGINS_CONFIG`에 추가합니다.  
*(주의: 파이썬 모듈명이므로 하이픈`-` 대신 언더스코어`_`를 사용합니다.)*

```python
# nautobot_config.py
PLUGINS = [
    "nautobot_plugin_nornir",
    "nautobot_golden_config",
    "nautobot_topology_views",
    "nautobot_ssot",
    "nautobot_device_lifecycle_mgmt",  # 신규 앱 모듈명
]

PLUGINS_CONFIG = {
    "nautobot_plugin_nornir": {
        "nornir_settings": {
            "credentials": "nautobot_plugin_nornir.plugins.credentials.nautobot_secrets.CredentialsNautobotSecrets",
        },
    },
    "nautobot_golden_config": {
        "enable_intended": True,
        "enable_compliance": True,
        "enable_backup": True,
    },
    "nautobot_topology_views": {
        "allow_coordinates_saving": True,
        "always_save_coordinates": False,
    },
    "nautobot_ssot": {
        "hide_example_jobs": False,
    },
    "nautobot_device_lifecycle_mgmt": {},  # 신규 앱 설정 (기본은 빈 딕셔너리)
}
```

### 3. 빌드 및 마이그레이션 반영
이미지를 다시 빌드하고 마이그레이션을 실행합니다.

```bash
# 이미지 재빌드
docker compose build --no-cache

# DB 마이그레이션
docker compose run --rm nautobot nautobot-server post_upgrade

# 서비스 시작
docker compose up -d
```

---

## 앱 옵션 변경

이미 설치된 앱의 설정값이나 기능 플래그만 변경할 때는 **이미지 재빌드가 필요 없습니다.**  
`nautobot_config.py`는 볼륨으로 연결되어 있어 컨테이너 재시작만으로 반영됩니다.

### 1. nautobot_config.py 수정
```python
# nautobot_config.py
PLUGINS_CONFIG = {
    "nautobot_golden_config": {
        "enable_intended": True,
        "enable_compliance": False,  # 변경할 옵션
        "enable_backup": True,
    },
}
```

### 2. 컨테이너 재시작
```bash
docker compose restart nautobot nautobot-worker nautobot-scheduler
```

---

## 운영 명령어

### 로그 확인
```bash
# Nautobot 웹 서버 로그
docker compose logs -f nautobot

# Celery Worker 로그
docker compose logs -f nautobot-worker

# 전체 서비스 로그
docker compose logs -f
```

### 서비스 제어
```bash
# 서비스 재시작
docker compose restart

# 백그라운드 시작
docker compose up -d

# 서비스 종료 (DB 데이터 보존)
docker compose down
```

### 마이그레이션 (운영 중)
컨테이너가 이미 실행 중일 때는 `exec`로 직접 마이그레이션을 수행할 수 있습니다.

```bash
# DB 마이그레이션만 실행
docker compose exec nautobot nautobot-server migrate

# 전체 업그레이드 작업 (마이그레이션 + 정적파일 + 캐시 정리)
docker compose exec nautobot nautobot-server post_upgrade
```

### 셸 접속
```bash
# 컨테이너 bash 접속
docker compose exec nautobot bash

# Nautobot nbshell (Django Shell) 접속
docker compose run --rm nautobot nautobot-server nbshell
```

### 데이터 및 이미지 완전 초기화
```bash
# 1. 컨테이너 및 볼륨(DB 데이터)만 삭제
docker compose down -v

# 2. 컨테이너, 볼륨, 빌드된/사용된 Docker 이미지까지 전부 완전 삭제
docker compose down -v --rmi all

# 3. (선택) 빌드 캐시까지 삭제하여 디스크 공간 완전 확보
docker builder prune -f
```
