"""agents/eda — STEP 3a Page 5 EDA 실엔진.

3원칙:
  ① LLM 판단 : 어떤 차트가 필요한지 추천 (제안)         → eda_engine._llm_recommend_charts
  ② 코드 실행: 추천된 차트의 데이터·통계 결정론 계산     → eda_engine.compute_chart_data
  ③ 자연어 코드: 사용자 한국어 → pandas/numpy 코드 (안전) → code_sandbox._validate_eda_code
"""
