# [HANDOFF] 단계: DL-1 (DB 연결 + catalog 접근 계층)

판정: **GATE PASS** (Master 검증 완료, 2026-06-08)

- 완료 커밋: A5 c2f9676(D-171 명세패치) + A6 ab66337(catalog/db 구현). push 미실행.
  (DL-1 마무리: D-172 + 이 핸드오프 = 추가 커밋 예정.)
- 게이트 증거:
  · A1 sync: branch feature/datalake-redesign, spec-1 3테이블·D-171 in-place, decisions max=171.
  · A2 baseline green: /api/health 200·backend:ok (풀 추가 후에도 = non-regression / import connect 0 = lazy 풀).
  · A3 권한: myeongsun CREATE on manufacturing=true (PG 16.14).
  · A4 백업/at-risk: 덤프 PGDMP custom-format(복원가능) + 비시스템 스키마 at-risk≈0(빈).
  · A7 throwaway(공유 5432 미접촉, 3중 격리: 55432·user=postgres·라이브스키마 0): 멱등 2회·get round-trip·list AND 필터·scalar/group(group_desc JSONB)·constraints JSONB·명시삭제·cleanup 전부 GREEN.
  · Phase B 라이브(첫 DB 쓰기): assert myeongsun/manufacturing/5432, datalake 스키마(owner=myeongsun)·3테이블·8인덱스, 멱등 2회, get round-trip(probe cleanup 잔여 0), additive before==after(metadata/lineage/agent_logs 불변), DROP 0·타 스키마 DML 0.
- 현재 상태:
  · 라이브 manufacturing.datalake = entries/columns/constraints 3테이블 + 8인덱스, 데이터 0. owner=myeongsun.
  · backend: db.py(asyncpg lazy 풀: get_pool/close_pool, 무인자 create_pool→PG* env, host 하드코딩 0) + catalog.py(MIGRATION_SQL, run_migration, get 라우터, CRUD: upsert_entry/get/list_entries/get_columns/get_constraints/delete_entry). baseline non-regression 유지.
  · datalake.get(id)→{data_path,modality} 결정론 라우터 동작(LLM 0, D-163). executor _resolve 치환은 미실행 = additive seam(DL-5, D-164).
- 변경 파일: backend/catalog.py(신규), backend/db.py(신규), spec-1_v5 §1-5(D-171 rename), decisions.md(D-171, +D-172), variable_index §8(D-171 교차참조 해당 시).
- 이탈/오픈:
  · D-172(upsert full-record-replace 계약) — 이 핸드오프 커밋에 포함.
  · .env override 5종(OLLAMA/MCP) 미적용 — DL-5 엔진결합 사안(현재 health 비의존).
  · R1 이월 트래킹 유지: STEP_1B-3a:245/256/267→DL-3, env-staging 6셀→DL-2/R-final, PipelineFull 예시→DL-3, analysis_groups shape→DL-4.
  · push 미실행 — 병갑 판정.
- 다음 단계: DL-2 (적재 도구 + KAMP 5.1G 적재). 진입조건:
  · DB 백업 = DL-2 진입 게이트(PROTOCOL §3). A4 적정 — datalake 생성 후에도 데이터 0이라 유효. 대량 ingest 전 fresh 스냅샷 1회 권장(롤백 granularity).
  · tools/datalake_ingest.py: ~/FINAL/1_data 스캔→메타 생성(modality=포맷/폴더, function=L1~L4+lines.yaml, site, vid=라인)→data/lake/<id>/ 복사 + catalog INSERT(upsert=full record, D-172).
  · ★ FFT 광폭/숫자헤더(L3 vibration) = column_kind=group descriptor 필수(D-161).
  · 멱등 재적재 + dry-run 먼저. 건수 일치(스캔=INSERT)·인코딩 깨짐 0·get 샘플 읽힘.
- 재개 지시: worktree ~/FINAL/0_BGS/datalake-redesign, branch feature/datalake-redesign, 읽기순서 DL_README→DL_BLUEPRINT→DL_PROTOCOL→이 핸드오프(DL-1).
