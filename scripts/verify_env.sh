#!/usr/bin/env bash
# 환경 토대 검증 (설계 대화에서 합의한 4개 체크)
set -e
echo "[1] Snap Docker 아님 확인 (비어있어야 정상):"
snap list 2>/dev/null | grep docker || echo "  OK (snap 아님)"
echo "[2] 호스트 GPU:"; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo "[3] nvidia 런타임 등록:"; cat /etc/docker/daemon.json 2>/dev/null | grep nvidia && echo "  OK"
echo "[4] 컨테이너에서 GPU 보임:"; docker run --rm --gpus all ubuntu:24.04 nvidia-smi -L
echo "== 4개 통과 시 환경 토대 완성 =="
