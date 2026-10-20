# 🌐 Nautobot Docker 가이드

Docker Compose 기반의 **Nautobot 3.1** 환경 운영 및 **앱(플러그인) 확장/설정 가이드**입니다.

---

## 📌 목차
1. [기본 환경 및 접속 정보](#-기본-환경-및-접속-정보)
2. [빠른 시작 (Quick Start)](#-빠른-시작-quick-start)
3. [새로운 App(플러그인) 추가 가이드](#-새로운-app플러그인-추가-가이드)
4. [App 옵션 및 세부 설정 변경 가이드](#-app-옵션-및-세부-설정-변경-가이드)
5. [자주 사용하는 운영 명령어](#-자주-사용하는-운영-명령어)

---

## 🖥 기본 환경 및 접속 정보

| 항목 | 정보 | 비고 |
| :--- | :--- | :--- |
| **Web UI 접속 주소** | `http://localhost:8888` | 호스트 8888 ➔ 컨테이너 8080 |
| **관리자 계정 (ID)** | `admin` | docker-compose.yml 설정 기준 |
| **관리자 비밀번호** | `admin` | 초기 비밀번호 |
| **API 토큰** | `0123456789abcdef0123456789abcdef01234567` | REST API / 자동화 연동용 |
| **주요 서비스** | Nautobot Web, Celery Worker, Celery Beat, PostgreSQL 15, Redis 7 | 5개 컨테이너 구성 |

---

## 🚀 빠른 시작 (Quick Start)

처음 환경을 구축하거나 전체 컨테이너를 올릴 때 실행하는 표준 절차입니다.

```bash
# 1. Compose 문법 및 파싱 상태 점검
docker compose config

# 2. 이미지 빌드 (캐시 제외)
docker compose build --no-cache

# 3. DB 스키마 마이그레이션 및 정적 파일 수집
docker compose run --rm nautobot nautobot-server post_upgrade

# 4. 모든 서비스 백그라운드 실행
docker compose up -d
```

> [!TIP]
> 웹 브라우저에서 `http://localhost:8888`로 접속한 뒤 `admin` / `admin`으로 로그인합니다.

---

## 🧩 새로운 App(플러그인) 추가 가이드

Nautobot에 새로운 앱(예: `nautobot-device-lifecycle-mgmt`, `nautobot-bgp-models` 등)을 설치하려면 **3개의 파일**을 확인 및 수정해야 합니다.

### Step 1. `Dockerfile`에 패키지 추가
새 앱을 설치하기 위해 `pip install` 목록에 패키지명을 추가합니다. (C 라이브러리나 OS 종속성이 필요한 경우 `apt-get` 영역에 추가)

```dockerfile
# Dockerfile 예시
...
# OS 종속성이 필요한 경우 여기에 추가
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    openssh-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 앱 패키지 설치 목록에 추가 (하이픈(-) 사용)
RUN pip install --no-cache-dir \
    nautobot-plugin-nornir \
    nautobot-golden-config \
    nautobot-device-lifecycle-mgmt  # <-- 새로 추가할 앱
...
```

---

### Step 2. `nautobot_config.py`의 `PLUGINS` 리스트에 등록
Nautobot이 앱을 로드할 수 있도록 Python 모듈명을 `PLUGINS` 리스트에 추가합니다.

> [!WARNING]
> PyPI 패키지명은 하이픈(`-`)을 주로 사용하지만, Python 모듈명은 **언더스코어(`_`)**를 사용해야 합니다.  
> 예: `nautobot-device-lifecycle-mgmt` (pip) ➔ `"nautobot_device_lifecycle_mgmt"` (PLUGINS)

```python
# nautobot_config.py 예시
PLUGINS = [
    "nautobot_plugin_nornir",
    "nautobot_golden_config",
    "nautobot_device_lifecycle_mgmt",  # <-- 언더스코어(_)로 등록
]
```

---

### Step 3. `nautobot_config.py`의 `PLUGINS_CONFIG`에 앱 옵션 선언
해당 앱에서 요구하거나 활성화할 설정값을 `PLUGINS_CONFIG` 딕셔너리에 정의합니다. 별도 설정이 필요 없더라도 빈 딕셔너리(`{}`)를 명시해 주는 것이 안전합니다.

```python
# nautobot_config.py 예시
PLUGINS_CONFIG = {
    "nautobot_plugin_nornir": {},
    "nautobot_golden_config": {
        "enable_intended": True,
        "enable_compliance": True,
        "enable_backup": True,
    },
    # 새로 추가한 앱의 옵션 설정
    "nautobot_device_lifecycle_mgmt": {
        # 앱 공식 문서의 설정 키-값 추가 (예시)
        # "barchart_bar_width": 0.1,
    },
}
```

---

### Step 4. 빌드 및 스키마 마이그레이션 (`post_upgrade`) 실행
새로운 패키지가 이미지에 들어가고 DB 테이블이 생성되어야 하므로 **빌드와 마이그레이션이 필수**입니다.

```bash
# 1. 새 패키지를 포함하여 이미지 재빌드
docker compose build --no-cache

# 2. 새 앱의 DB 테이블 마이그레이션 실행 (중요!)
docker compose run --rm nautobot nautobot-server post_upgrade

# 3. 변경된 이미지로 서비스 재시작
docker compose up -d
```

---

## ⚙️ App 옵션 및 세부 설정 변경 가이드

이미 설치된 앱의 **옵션(ON/OFF 또는 설정값)만 변경**할 때의 절차입니다.  
`nautobot_config.py`는 볼륨으로 호스트와 컨테이너가 직접 연결되어 있으므로, **도커 이미지를 다시 빌드할 필요가 없습니다.**

### 1. `nautobot_config.py` 파일 수정
`PLUGINS_CONFIG` 딕셔너리에서 원하는 기능의 플래그를 수정합니다.

```python
# nautobot_config.py
PLUGINS_CONFIG = {
    "nautobot_golden_config": {
        "enable_intended": True,   # 설계된 표준 설정(Intended Config) ON / OFF
        "enable_compliance": True, # 컴플라이언스 분석 ON / OFF
        "enable_backup": True,     # 장비 CLI 설정 백업 ON / OFF
    },
}
```

### 2. 컨테이너 재시작 (즉시 반영)
설정 파일이 다시 읽혀지도록 컨테이너만 재시작합니다.

```bash
# Nautobot 웹, 워커, 스케줄러 재시작 (수 초 내 완료)
docker compose restart nautobot nautobot-worker nautobot-scheduler
```

> [!NOTE]
> DB 스키마가 변경되지 않는 단순 설정값/옵션 토글은 `post_upgrade`나 `build` 과정 없이 `restart`만으로 즉시 적용됩니다.

---

## 🛠 자주 사용하는 운영 명령어

### 서비스 상태 및 로그 모니터링
```bash
# 전체 컨테이너 상태 확인
docker compose ps

# Nautobot 웹 서버 실시간 로그 확인
docker compose logs -f nautobot

# 백그라운드 워커 로그 확인 (잡 실행 로그)
docker compose logs -f nautobot-worker

# 전체 서비스 로그 확인
docker compose logs -f
```

### 서비스 중지 및 재시작
```bash
# 서비스 일시 정지 없이 재시작
docker compose restart

# 모든 서비스 정상 종료 (데이터는 볼륨에 보존)
docker compose down

# 모든 서비스 백그라운드 시작
docker compose up -d
```

### 컨테이너 내부 셸 접속 및 관리 명령어
```bash
# 1. [운영 중] 실행 중인 컨테이너에서 즉시 DB 마이그레이션만 실행
docker compose exec nautobot nautobot-server migrate

# 2. [운영 중] 실행 중인 컨테이너에서 post_upgrade(마이그레이션+정적파일+캐시정리) 실행
docker compose exec nautobot nautobot-server post_upgrade

# 3. Nautobot 컨테이너 bash 접속
docker compose exec nautobot bash

# 4. Nautobot 관리자 셸(Django Shell) 실행
docker compose run --rm nautobot nautobot-server nbshell
```

### 초기화 (주의: 모든 DB 데이터 삭제)
```bash
# 컨테이너 및 볼륨(DB 데이터) 완전 삭제
docker compose down -v
```
