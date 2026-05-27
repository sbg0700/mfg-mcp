"""
synthetic/generate.py
=====================
KAMP 실증 데이터의 "지저분함"을 모사한 더미 timeseries 데이터 생성기.

⚠️ 이 더미의 목적은 '깨끗한 합성 데이터의 함정'을 피하는 것이다.
   일부러 8가지 챌린지(인계서 [5])를 심어서, Inspector/전처리 파이프라인이
   현장 데이터의 고통점을 실제로 잡아내는지 검증할 수 있게 한다.

생성 파일 (data/synthetic/timeseries/ 아래):
  1) mct_tool_manage_clean.csv      — 가벼운 정상 케이스 (수직 슬라이스 1차 타깃)
  2) mold_anomaly_headerless.csv    — [챌린지 2] 헤더가 첫 데이터 행 (header=None 필요)
  3) cnc_lathe_masked.csv           — [챌린지 3] '*','**','***' 마스킹 + dtype 혼재
  4) order_cp949.csv                — [챌린지 1] CP949 인코딩 + 한글 컬럼
  5) press_imbalance.csv            — [챌린지 6] PASS_YN 2.85% 극심 불균형

실데이터 교체 시: 이 파일들을 진짜 KAMP CSV로 바꾸기만 하면 MCP 서버는 그대로 동작.
"""

from __future__ import annotations
import os
import numpy as np
import pandas as pd

OUT_DIR = os.path.join(os.path.dirname(__file__), "timeseries")
RNG = np.random.default_rng(42)


def _ensure_dir() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)


def gen_clean_mct(n: int = 1628) -> str:
    """1) 가벼운 정상 timeseries (mct_tool_manage 모사, 1.6K행).
    수직 슬라이스의 첫 타깃. 인코딩 챌린지 가벼움."""
    t0 = pd.Timestamp("2024-03-01 08:00:00")
    df = pd.DataFrame({
        "gdatetime": [t0 + pd.Timedelta(seconds=12 * i) for i in range(n)],
        "fcycleTime": RNG.normal(12.0, 0.4, n).round(3),
        "fspindleRPM1": RNG.integers(8000, 12000, n),
        "fspindleTroq1": RNG.normal(45.0, 6.0, n).round(2),
        "ftoolNum": RNG.integers(1, 9, n),
        "gmv": RNG.normal(220.0, 3.0, n).round(2),     # 전압
        "gma": RNG.normal(11.5, 1.2, n).round(3),       # 전류
    })
    # 살짝의 결측 (현실성)
    df.loc[RNG.choice(n, size=int(n * 0.01), replace=False), "fspindleTroq1"] = np.nan
    path = os.path.join(OUT_DIR, "mct_tool_manage_clean.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def gen_headerless(n: int = 5000) -> str:
    """2) [챌린지 2-③] 헤더가 첫 측정값인 케이스 (header=None 후 처리 필요).
    원본 mold_anomaly 모사. 헤더 행 없이 숫자만 쏟아짐."""
    data = np.column_stack([
        np.arange(n),
        RNG.normal(100, 15, n).round(2),
        RNG.normal(50, 8, n).round(2),
        RNG.integers(0, 2, n),
        RNG.normal(0.5, 0.1, n).round(4),
    ])
    df = pd.DataFrame(data)
    path = os.path.join(OUT_DIR, "mold_anomaly_headerless.csv")
    # ★헤더 없이 저장 → 첫 행이 데이터. Inspector가 이걸 감지해야 함
    df.to_csv(path, index=False, header=False, encoding="utf-8-sig")
    return path


def gen_masked(n: int = 3000) -> str:
    """3) [챌린지 3] 마스킹 카테고리 '*','**','***' 혼재 → object dtype 오염.
    원본 cnc_lathe_quality 모사."""
    servo_load = RNG.normal(60, 12, n).round(2).astype(object)
    # 약 8%를 마스킹 문자열로 오염 (보안/익명화로 흔히 발생)
    mask_idx = RNG.choice(n, size=int(n * 0.08), replace=False)
    masks = RNG.choice(["*", "**", "***"], size=len(mask_idx))
    for i, m in zip(mask_idx, masks):
        servo_load[i] = m
    df = pd.DataFrame({
        "TagId": [f"TAG_{i % 5:02d}" for i in range(n)],
        "CNC_ServoLoad_1": servo_load,            # ★혼재: float + '*'/'**'/'***'
        "CNC_ServoCurrentPct_1": RNG.normal(40, 9, n).round(2),
        "Quality": RNG.choice(["OK", "NG"], size=n, p=[0.95, 0.05]),
        "Value": RNG.normal(1.0, 0.05, n).round(4),
    })
    path = os.path.join(OUT_DIR, "cnc_lathe_masked.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def gen_cp949_order(n: int = 2000) -> str:
    """4) [챌린지 1] CP949 인코딩 + 한글 컬럼명.
    원본 고객사_모델별_주문량 모사. utf-8로 읽으면 깨짐 → 인코딩 자동 감지 시연용."""
    t0 = pd.Timestamp("2024-01-01")
    df = pd.DataFrame({
        "uid": np.arange(1, n + 1),
        "order_date": [(t0 + pd.Timedelta(days=int(i) // 5)).strftime("%Y-%m-%d") for i in range(n)],
        "제품코드": [f"P{RNG.integers(1000, 9999)}" for _ in range(n)],
        "제품명": RNG.choice(["브래킷", "하우징", "커넥터", "샤프트"], size=n),
        "예측수량": RNG.integers(100, 5000, n),
        "실제수량": RNG.integers(100, 5000, n),
        "오차율(%)": RNG.normal(0, 8, n).round(2),
    })
    path = os.path.join(OUT_DIR, "order_cp949.csv")
    # ★CP949로 저장 → utf-8 디폴트 리더로 읽으면 UnicodeDecodeError
    df.to_csv(path, index=False, encoding="cp949")
    return path


def gen_imbalance(n: int = 10000) -> str:
    """5) [챌린지 6] PASS_YN 2.85% 극심 클래스 불균형.
    원본 press_forming 모사. 불량 라벨이 극소수."""
    n_fail = int(n * 0.0285)
    pass_yn = np.array(["Y"] * (n - n_fail) + ["N"] * n_fail)
    RNG.shuffle(pass_yn)
    df = pd.DataFrame({
        "ITEM_CODE": [f"IT{RNG.integers(100, 999)}" for _ in range(n)],
        **{f"VALUE{i}": RNG.normal(50, 10, n).round(2) for i in range(1, 6)},
        "PASS_YN": pass_yn,
    })
    path = os.path.join(OUT_DIR, "press_imbalance.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def gen_injection_machine(n: int = 800) -> str:
    """6) [우려 1] 공정 의미 그룹이 풍부한 사출 성형 데이터.
    실제 KAMP L1_cnc_machine_optimize 구조 모사:
    - 사출 시퀀스 (1ST~10TH INJECTION VELOCITY) — 시퀀스 보존 정규화 대상
    - 보압 프로파일 (PACK PRESSURE 1~6, PACK TIME 1~6) — 프로파일 그룹
    - 메타 (LOT No., TimeStamp, EQP_ID) — 정규화 제외
    - 단독 (BACK PRESSURE)"""
    data = {
        "LOT No.": [f"LOT{2024000+i}" for i in range(n)],
        "TimeStamp": pd.date_range("2024-01-08 11:20", periods=n, freq="min").astype(str),
        "EQP_ID": [f"EQP{RNG.integers(1,6)}" for _ in range(n)],
    }
    # 사출 시퀀스: 1차→10차 점증 추세 (시퀀스 의미 — 독립정규화하면 소실)
    for step in range(1, 11):
        base = 40 + step * 3  # 단계별 점증
        suffix = {1:"1ST",2:"2ND",3:"3RD"}.get(step, f"{step}TH")
        data[f"{suffix} INJECTION VELOCITY"] = RNG.normal(base, 4, n).round(2)
    # 사출 스위치 위치 (9단계)
    for step in range(1, 10):
        suffix = {1:"1ST",2:"2ND",3:"3RD"}.get(step, f"{step}TH")
        data[f"{suffix} INJECTION SWITCH POS"] = RNG.normal(20 + step*2, 2, n).round(2)
    # 보압 프로파일 (1~6)
    for i in range(1, 7):
        data[f"PACK PRESSURE {i}"] = RNG.normal(100 - i*5, 6, n).round(2)
        data[f"PACK TIME {i}"] = RNG.normal(2 + i*0.5, 0.3, n).round(2)
    # 단독
    data["BACK PRESSURE"] = RNG.normal(80, 10, n).round(2)
    df = pd.DataFrame(data)
    path = os.path.join(OUT_DIR, "cnc_machine_injection.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def main() -> None:
    _ensure_dir()
    results = [
        ("clean (정상, 1차 타깃)", gen_clean_mct()),
        ("챌린지2 헤더없음", gen_headerless()),
        ("챌린지3 마스킹+dtype혼재", gen_masked()),
        ("챌린지1 CP949+한글", gen_cp949_order()),
        ("챌린지6 극심불균형 2.85%", gen_imbalance()),
        ("우려1 공정의미그룹(사출시퀀스)", gen_injection_machine()),
    ]
    print("=" * 60)
    print("더미 timeseries 데이터 생성 완료")
    print("=" * 60)
    for label, path in results:
        size_kb = os.path.getsize(path) / 1024
        print(f"  [{label:28s}] {os.path.basename(path):28s} {size_kb:8.1f} KB")
    print(f"\n위치: {OUT_DIR}")


if __name__ == "__main__":
    main()
