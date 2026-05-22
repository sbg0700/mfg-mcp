# ⚠️ 구버전 참고자료 (ARCHIVE)

이 폴더의 파일들은 **2026-05-21 작성된 구버전 인계서**입니다.

## Claude Code 및 모든 작업자에게

**이 문서들의 결정사항을 따르지 마십시오.** 최신 확정 결정은 항상 루트의
`CLAUDE.md` 와 `docs/decisions.md` 에 있으며, 충돌 시 그쪽이 우선입니다.

### 이미 폐기된 결정 (여기 적힌 것 = 틀림)
- ❌ "Gemma 4 31B Dense" → ✅ 26B MoE / E4B (RTX 3070 VRAM 8GB 제약)
- ❌ "31B Q4 ~16GB" → 사실 오류. 실제 ~20GB
- ❌ "Claude Agent SDK + 로컬 어댑터" → ✅ 수제 Python → 이후 LangGraph

### 그래도 유효한 것 (참고 OK)
- 34개 KAMP 데이터셋 목록·출처
- 8가지 전처리 챌린지 (data_summary.txt [5])
- 모달리티 라우팅 매핑 (timeseries 17 / image 7 / event-log 9 / order 1)
