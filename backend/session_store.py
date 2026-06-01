"""
backend/session_store.py — STEP 1B-2a 인메모리 PipelineSession 저장소.

Resumable Orchestrator의 상태 머신을 인메모리 dict에 저장한다.
패턴: harness/lineage.py의 _STORE와 동일. Sprint 2에서 PostgreSQL로 이전.

세션 라이프사이클:
  created → running → (awaiting_approval ↔ running)* → completed (or error)

★폴링형 설계 (D-51)★: blocking awaiter 없음. suspend = 상태 저장 + 즉시 응답.
사용자는 /approve로 step_key를 누적 승인하고, /execute_pipeline 재호출로 resume.
"""
from __future__ import annotations
import uuid
from typing import Any

# 모듈 전역 — 같은 프로세스 내 모든 핸들러가 공유 (lineage._STORE 패턴)
_SESSIONS: dict[str, dict[str, Any]] = {}


def create_session(pipeline_full: dict) -> str:
    """pipeline_full(Page 2 1-1 + Page 3 1-2 출력)을 받아 세션 생성.
    session_id(uuid4) 반환."""
    sid = str(uuid.uuid4())
    _SESSIONS[sid] = {
        "session_id": sid,
        "pipeline_full": pipeline_full,
        "status": "created",                  # created|running|awaiting_approval|completed|error
        "approved_step_keys": [],             # 누적 (list — JSON 직렬화 위해 set 아님)
        "completed_stage_orders": [],         # resume 시 skip
        "completed_module_keys": [],          # resume 시 skip ("stage.idx" 형식)
        "accumulated_context": [],            # Stage별 요약 누적 (1B-2b Aggregator 입력)
        "module_results": {},                 # module_key -> {profile,plan,execution,validation}
        "pending": None,                      # 현재 멈춘 지점 (suspend 시 채움)
        "alarms": [],                         # llm_judge_data_necessity 기록
    }
    return sid


def get_session(sid: str) -> dict | None:
    return _SESSIONS.get(sid)


def save_session(sid: str, session: dict) -> None:
    """세션 갱신. dict는 reference로 공유되므로 이 호출은 미래의 외부저장 이전을 위한 훅."""
    _SESSIONS[sid] = session


def list_sessions() -> list[str]:
    """디버그/테스트용 — 현재 보관 중인 세션 id 목록."""
    return list(_SESSIONS.keys())


def public_view(session: dict) -> dict:
    """사용자/UI에 노출할 안전한 뷰. pipeline_full은 포함 (디버그 + UI 진행 표시).
    완전한 module_results는 큰 데이터 포함 가능하나, FastAPI JSON 직렬화는 dict/list 기반이므로 그대로 통과.
    STEP 1B-3d: model 필드 노출 (D-99) — ModelDropdown이 GET /sessions/{id}로 동기화."""
    return {
        "session_id": session.get("session_id"),
        "status": session.get("status"),
        "pending": session.get("pending"),
        "approved_step_keys": list(session.get("approved_step_keys", [])),
        "completed_stage_orders": list(session.get("completed_stage_orders", [])),
        "completed_module_keys": list(session.get("completed_module_keys", [])),
        "alarms": list(session.get("alarms", [])),
        "accumulated_context": list(session.get("accumulated_context", [])),
        "module_results": session.get("module_results", {}),
        "pipeline_full": session.get("pipeline_full"),
        "model": session.get("model"),
    }
