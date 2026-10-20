# 최신 규격인 Nautobot 3.1 및 Python 3.12 기반 공식 이미지 사용
FROM networktocode/nautobot:3.1-py3.12

USER root

# Nornir SSH 접속 및 Git 연동용 필수 OS 종속성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    openssh-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 최신 Golden Config 및 의존 플러그인(Nornir) 설치
RUN pip install --no-cache-dir \
    nautobot-plugin-nornir \
    nautobot-golden-config

USER nautobot

