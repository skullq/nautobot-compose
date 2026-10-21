# 최신 규격인 Nautobot 3.1 및 Python 3.12 기반 공식 이미지 사용
FROM networktocode/nautobot:3.1-py3.12

USER root

# Nornir SSH 접속 및 Git 연동용 필수 OS 종속성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    openssh-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 최신 Golden Config 및 의존 플러그인(Nornir, Topology Views, SSoT) 설치
# 주의: scrapli 2026.x는 nornir-scrapli(2025.x)와 호환되지 않으므로 scrapli<2026으로 영구 고정
RUN pip install --no-cache-dir \
    "scrapli<2026" \
    nautobot-plugin-nornir \
    nautobot-golden-config \
    "nautobot-topology-views==4.5.1.1" \
    "nautobot-ssot==4.7.0"

# 로컬 Git 저장소 마운트 연동을 위한 safe.directory 설정
RUN git config --system --add safe.directory "*"

USER nautobot
RUN git config --global --add safe.directory "*"

