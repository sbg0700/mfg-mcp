"""
synthetic/generate_order.py — KAMP order(주문·생산량) 모사 더미.

모사 구조 (data_summary.txt):
  - ★CP949 인코딩 + 한글 헤더 (챌린지1): 고객사_모델별_주문량
  - 주문 다변량 시계열 → 생산량 예측
  - 헤더: uid, order_date, 제품코드, 제품명, 제품군분류, 생산구분, 주문량...

생성:
  order_demand_cp949.csv — CP949 인코딩, 한글 헤더, 주문 다변량 [챌린지: CP949+한글헤더]
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

np.random.seed(42)
OUT = os.path.join(os.path.dirname(__file__), "order")


def gen_order_demand() -> dict:
    n = 1000
    products = ["PCB-A1", "BMS-X2", "MOD-C3", "PKG-D4"]
    groups = ["전장", "배터리", "모듈", "포장"]
    df = pd.DataFrame({
        "uid": range(1, n + 1),
        "order_date": pd.date_range("2024-01-01", periods=n, freq="h").strftime("%Y-%m-%d"),
        "제품코드": np.random.choice(products, n),
        "제품명": np.random.choice(["피씨비조립", "배터리팩", "제어모듈", "외장패키지"], n),
        "제품군분류": np.random.choice(groups, n),
        "생산구분": np.random.choice(["양산", "시작", "긴급"], n, p=[0.7, 0.2, 0.1]),
        "주문량": np.random.randint(100, 5000, n),
        "현재고주문량": np.random.randint(0, 2000, n),
        "종주문잔량": np.random.randint(0, 1000, n),
    })
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "order_demand_cp949.csv")
    # ★CP949로 저장 (한글 인코딩 챌린지)
    df.to_csv(path, index=False, encoding="cp949")
    return {"dataset": "order_demand_cp949.csv", "rows": n,
            "challenges": ["CP949 인코딩 (한글)", "한글 헤더", "주문 다변량 시계열"]}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    r = gen_order_demand()
    print("=" * 64)
    print("order 합성 더미 생성 완료 (KAMP 구조 모사)")
    print("=" * 64)
    print(f"\n  [{r['dataset']}] {r['rows']}행")
    for c in r["challenges"]:
        print(f"     - 챌린지: {c}")
    print(f"\n위치: {OUT}")


if __name__ == "__main__":
    main()
