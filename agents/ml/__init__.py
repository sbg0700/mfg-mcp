"""agents/ml — STEP 3c Page 6 ML 학습 실엔진.

3원칙:
  ① LLM이 추천 — 모델 종류 + fit_score (기존 /recommend, 회귀 0)
  ② 코드가 학습 — scikit-learn/xgboost 결정론 (LLM 0). random_state=42 재현성
  ③ 규칙이 안전 거름 — 파라미터 화이트리스트(clamp+notice) + OOM 가드
"""
