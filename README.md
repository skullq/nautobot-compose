# Nautobot Docker 가이드

로컬 환경에서 네트워크 자동화 및 SoT(Source of Truth) 테스트를 위한 Docker Compose 기반 Nautobot 3.1 배포 가이드입니다.  
Golden Config 플러그인이 기본 포함되어 있으며, 필요에 따라 추가 앱(플러그인)을 설치하고 설정할 수 있습니다.  

> **주의**: 보안을 고려하지 않은 구성이므로 외부 공개 없이 로컬 환경에서만 사용하세요.

---

## 목차
1. [기본 접속 정보](#기본-접속-정보)
2. [초기 실행 (Quick Start)](#초기-실행-quick-start)
3. [신규 앱(플러그인) 추가](#신규-앱플러그인-추가)
4. [앱 옵션 변경](#앱-옵션-변경)
5. [운영 명령어](#운영-명령어)

---

## 기본 접속 정보

| 항목 | 내용 |
| :--- | :--- |
| **Web UI** | `http://localhost:8888` |
| **계정** | ID: `admin` / PW: `admin` |
| **API Token** | `0123456789abcdef0123456789abcdef01234567` |
| **구성 컨테이너** | Nautobot Web, Celery Worker, Celery Beat, PostgreSQL 15, Redis 7 |

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

## 신규 앱(플러그인) 추가

새로운 Nautobot 앱을 설치할 때는 다음 3단계를 진행합니다.

### 1. Dockerfile 수정
설치할 패키지를 `pip install` 목록에 추가합니다. (OS 라이브러리가 필요하면 `apt-get`에 추가)

```dockerfile
# Dockerfile
RUN pip install --no-cache-dir \
    nautobot-plugin-nornir \
    nautobot-golden-config \
    nautobot-device-lifecycle-mgmt  # 신규 패키지명 (하이픈 사용)
```

### 2. nautobot_config.py 등록
앱 모듈명을 `PLUGINS` 및 `PLUGINS_CONFIG`에 추가합니다.  
*(주의: 파이썬 모듈명이므로 하이픈`-` 대신 언더스코어`_`를 사용합니다.)*

```python
# nautobot_config.py
PLUGINS = [
    "nautobot_plugin_nornir",
    "nautobot_golden_config",
    "nautobot_device_lifecycle_mgmt",  # 신규 앱 모듈명
]

PLUGINS_CONFIG = {
    "nautobot_plugin_nornir": {},
    "nautobot_golden_config": {
        "enable_intended": True,
        "enable_compliance": True,
        "enable_backup": True,
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
