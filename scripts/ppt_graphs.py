"""scripts/ppt_graphs.py — 측정 PPT 그래프 세트 (한글, Noto Sans KR).

데이터: /tmp/measure_results.csv(cold) + measure_results_warm.csv(warm).
스토리 5단계(A~E) 개별 PNG + 합본 1장. 160dpi.
색: e4b=blue(#2563eb), 26b=orange(#ea580c), 한계선=red(#dc2626), 적합=green(#16a34a).
기호 ✓/✗/→ 는 Noto Sans KR에 없음 → 텍스트("적합"/"초과") + arrowprops 도형으로 대체.
"""
from __future__ import annotations
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ── 한글 폰트 등록 ──
_FONT = "/home/byeonggab89/.fonts/NotoSansKR.ttf"
fm.fontManager.addfont(_FONT)
_KR = fm.FontProperties(fname=_FONT).get_name()

OUT = "scripts/ppt_assets"
os.makedirs(OUT, exist_ok=True)

C_E4B = "#2563eb"
C_26B = "#ea580c"
C_LIMIT = "#dc2626"
C_GOOD = "#16a34a"
C_BAD = "#dc2626"
C_GRID = "#cbd5e1"

plt.rcParams.update({
    "font.family": _KR,
    "axes.unicode_minus": False,
    "font.size": 12,
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "axes.labelsize": 12,
    "axes.grid": True,
    "grid.color": C_GRID,
    "grid.alpha": 0.4,
    "grid.linewidth": 0.7,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

DS_ORDER = ["L1_injection_production", "L3_vacuum_pump", "L3_elevator_vibration"]
DS_LABELS = {
    "L1_injection_production": "184행\n(작은)",
    "L3_vacuum_pump": "43,236행\n(중간)",
    "L3_elevator_vibration": "210,000행\n(큰)",
}
DS_ROWS = {"L1_injection_production": 184, "L3_vacuum_pump": 43236,
           "L3_elevator_vibration": 210000}


def load(path):
    d = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            d[(r["model"], r["dataset"])] = r
    return d


COLD = load("/tmp/measure_results.csv")
WARM = load("/tmp/measure_results_warm.csv")


def bar_labels(ax, bars, fmt="{:.1f}", fs=10):
    for b in bars:
        h = b.get_height()
        ax.annotate(fmt.format(h), (b.get_x() + b.get_width() / 2, h),
                    ha="center", va="bottom", fontsize=fs, fontweight="bold",
                    xytext=(0, 2), textcoords="offset points")


def caption(fig, text, y=0.015):
    fig.text(0.5, y, text, ha="center", fontsize=10.5, style="italic", color="#334155")


# ─── A: 모델별 추론 시간 ───
def graph_A(ax=None, standalone=True):
    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 5.5))
    x = range(len(DS_ORDER))
    w = 0.38
    e = [float(COLD[("gemma4:e4b", d)]["total_s"]) for d in DS_ORDER]
    m = [float(COLD[("gemma4:26b", d)]["total_s"]) for d in DS_ORDER]
    b1 = ax.bar([i - w / 2 for i in x], e, w, label="gemma4:e4b", color=C_E4B)
    b2 = ax.bar([i + w / 2 for i in x], m, w, label="gemma4:26b", color=C_26B)
    bar_labels(ax, b1, "{:.1f}초")
    bar_labels(ax, b2, "{:.1f}초")
    ax.set_xticks(list(x))
    ax.set_xticklabels([DS_LABELS[d] for d in DS_ORDER])
    ax.set_ylabel("총 추론 시간 (초)")
    ax.set_title("모델별 추론 시간 — 26b는 e4b 대비 5.6~15배 느림")
    ax.legend(loc="upper right", framealpha=0.9)
    ax.set_ylim(0, max(m) * 1.2)
    if standalone:
        caption(ax.figure, "제한 스펙(8GB)에서 e4b는 10~25초, 26b는 125~175초 — 무거운 모델은 큰 지연 비용을 치른다.")
        ax.figure.subplots_adjust(bottom=0.16, top=0.9)
        p = f"{OUT}/graph_A_time.png"
        ax.figure.savefig(p, dpi=160); plt.close(ax.figure); return p


# ─── B: VRAM + 8GB 한계 ───
def graph_B(ax=None, standalone=True):
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5.5))
    e_v = float(COLD[("gemma4:e4b", "L1_injection_production")]["vram_peak_mb"])
    m_v = float(COLD[("gemma4:26b", "L3_vacuum_pump")]["vram_peak_mb"])
    bars = ax.bar(["gemma4:e4b", "gemma4:26b"], [e_v, m_v],
                  color=[C_E4B, C_26B], width=0.5)
    bar_labels(ax, bars, "{:.0f} MB", fs=12)
    # 8GB 한계선
    ax.axhline(8192, color=C_LIMIT, ls="--", lw=2)
    ax.text(1.45, 8192, "RTX 3070 — 8GB 한계", color=C_LIMIT, fontsize=11,
            fontweight="bold", va="bottom", ha="right")
    # 26b 오프로딩 주석
    ax.annotate("+ CPU 오프로딩 63%\n(19GB 모델을 7GB+CPU로 분산)",
                (1, m_v), xytext=(1, m_v + 1600), ha="center", fontsize=10.5,
                fontweight="bold", color=C_26B,
                arrowprops=dict(arrowstyle="->", color=C_26B, lw=1.5))
    ax.set_ylabel("VRAM peak (MB)")
    ax.set_title("VRAM 사용량 — 26b는 8GB 한계 근접, CPU 분산 구동")
    ax.set_ylim(0, 11000)
    if standalone:
        caption(ax.figure, "e4b는 VRAM 내 완전 적재(3.5GB), 26b는 19GB 모델을 7GB+CPU로 분산 — 8GB로는 부족.")
        ax.figure.subplots_adjust(bottom=0.12, top=0.9)
        p = f"{OUT}/graph_B_vram.png"
        ax.figure.savefig(p, dpi=160); plt.close(ax.figure); return p


# ─── C: 행수 vs 시간 (병목 발견) ───
def graph_C(ax=None, standalone=True):
    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 5.5))
    rows = [DS_ROWS[d] for d in DS_ORDER]
    e = [float(COLD[("gemma4:e4b", d)]["total_s"]) for d in DS_ORDER]
    m = [float(COLD[("gemma4:26b", d)]["total_s"]) for d in DS_ORDER]
    ax.plot(rows, e, "o-", color=C_E4B, lw=2.5, ms=9, label="gemma4:e4b")
    ax.plot(rows, m, "s-", color=C_26B, lw=2.5, ms=9, label="gemma4:26b")
    for r, v in zip(rows, e):
        ax.annotate(f"{v:.1f}초", (r, v), xytext=(0, -16), textcoords="offset points",
                    ha="center", fontsize=9.5, color=C_E4B, fontweight="bold")
    ax.set_xscale("log")
    ax.set_xlabel("데이터 행수 (로그 스케일)")
    ax.set_ylabel("총 추론 시간 (초)")
    ax.set_title("데이터 크기 vs 시간 — 시간이 행수에 비례하지 않음")
    ax.legend(loc="center right", framealpha=0.9)
    # 역전 강조: e4b 184행(24.6) > 210k행(10.6)
    ax.annotate("데이터 1000배인데 더 빠름\n병목은 데이터가 아니라 LLM",
                (rows[0], e[0]), xytext=(rows[1] * 0.5, e[0] + 6),
                ha="center", fontsize=11, fontweight="bold", color="#7c2d12",
                arrowprops=dict(arrowstyle="->", color="#7c2d12", lw=1.8))
    ax.annotate("", (rows[2], e[2]), xytext=(rows[0], e[0]),
                arrowprops=dict(arrowstyle="->", color="#7c2d12", lw=1.2, ls=":"))
    ax.set_ylim(0, max(m) * 1.15)
    if standalone:
        caption(ax.figure, "전처리(결정론)는 빠름, LLM 추론(inspect+plan)이 시간 지배 = 트러블슈팅의 출발점.")
        ax.figure.subplots_adjust(bottom=0.14, top=0.9)
        p = f"{OUT}/graph_C_rows_vs_time.png"
        ax.figure.savefig(p, dpi=160); plt.close(ax.figure); return p


# ─── D: 워밍업 before/after (좌우 2 서브플롯) ───
def _warm_subplot(ax, model, title):
    x = range(len(DS_ORDER))
    w = 0.38
    bef = [float(COLD[(model, d)]["total_s"]) for d in DS_ORDER]
    aft = [float(WARM[(model, d)]["total_s"]) for d in DS_ORDER]
    b1 = ax.bar([i - w / 2 for i in x], bef, w, label="before (콜드)", color="#94a3b8")
    col = C_E4B if "e4b" in model else C_26B
    b2 = ax.bar([i + w / 2 for i in x], aft, w, label="after (워밍)", color=col)
    bar_labels(ax, b1, "{:.0f}", fs=9)
    bar_labels(ax, b2, "{:.0f}", fs=9)
    # 단축% 라벨
    for i, (bv, av) in enumerate(zip(bef, aft)):
        pct = (bv - av) / bv * 100
        improved = pct > 3
        ax.annotate(f"{pct:+.0f}%",
                    (i, max(bv, av)), xytext=(0, 16), textcoords="offset points",
                    ha="center", fontsize=10.5, fontweight="bold",
                    color=C_GOOD if improved else C_BAD)
    ax.set_xticks(list(x))
    ax.set_xticklabels([DS_LABELS[d] for d in DS_ORDER], fontsize=10)
    ax.set_title(title, fontsize=13, pad=10)
    ax.legend(loc="upper right", fontsize=9.5, framealpha=0.9)
    ax.set_ylim(0, max(max(bef), max(aft)) * 1.32)   # 라벨/범례 공간


def graph_D(axes=None, standalone=True):
    if axes is None:
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=False)
    _warm_subplot(axes[0], "gemma4:e4b", "e4b — 콜드 로딩이 병목이었음 (개선)")
    _warm_subplot(axes[1], "gemma4:26b", "26b — VRAM 변화 0인데도 불안정 (변동)")
    axes[0].set_ylabel("총 추론 시간 (초)")
    axes[1].annotate("콜드 로딩 제거(VRAM 변화 0)에도\nCPU 오프로딩 변동성 지배",
                     (1, float(WARM[("gemma4:26b", "L3_vacuum_pump")]["total_s"])),
                     xytext=(0.05, 205), fontsize=10, fontweight="bold", color=C_BAD,
                     ha="left",
                     arrowprops=dict(arrowstyle="->", color=C_BAD, lw=1.3))
    if standalone:
        fig = axes[0].figure
        fig.suptitle("콜드 로딩 최적화(keep-alive 워밍업) — e4b 개선, 26b 변동",
                     fontsize=16, fontweight="bold", y=0.98)
        caption(fig, "e4b: 콜드 로딩이 병목이었음(평균 33% 단축). 26b: CPU 오프로딩 변동성이 지배 (워밍업 무력).")
        fig.subplots_adjust(bottom=0.15, top=0.86, wspace=0.18)
        p = f"{OUT}/graph_D_warmup.png"
        fig.savefig(p, dpi=160); plt.close(fig); return p


# ─── E: 종합 결론 매트릭스 ───
def graph_E(ax=None, standalone=True):
    if ax is None:
        fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.axis("off")
    cols = ["", "추론 시간", "VRAM", "8GB 적합성", "워밍업 효과", "결론"]
    e4b_row = ["gemma4:e4b", "빠름 (10~25초)", "3.5 GB", "적합", "33% 개선", "제한 공장 도입 가능"]
    m26_row = ["gemma4:26b", "느림 (125~175초)", "7.3 GB", "초과", "불안정", "24GB+ GPU 전제"]
    table = ax.table(cellText=[e4b_row, m26_row], colLabels=cols,
                     cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 2.4)
    # 색칠: e4b 행 초록 톤, 26b 행 빨강 톤, "적합성/결론" 강조
    ncol = len(cols)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#cbd5e1")
        if r == 0:  # 헤더
            cell.set_facecolor("#1e293b"); cell.set_text_props(color="white", fontweight="bold")
        elif r == 1:  # e4b
            cell.set_facecolor("#dcfce7" if c in (3, 5) else "#f0fdf4")
            if c in (3, 5): cell.set_text_props(color=C_GOOD, fontweight="bold")
        elif r == 2:  # 26b
            cell.set_facecolor("#fee2e2" if c in (3, 5) else "#fef2f2")
            if c in (3, 5): cell.set_text_props(color=C_BAD, fontweight="bold")
        if c == 0: cell.set_text_props(fontweight="bold")
    ax.set_title("종합 — 제한 스펙(8GB)에선 e4b + keep-alive가 정답",
                 fontsize=15, fontweight="bold", pad=20)
    if standalone:
        ax.figure.subplots_adjust(top=0.82, bottom=0.05)
        p = f"{OUT}/graph_E_summary.png"
        ax.figure.savefig(p, dpi=160); plt.close(ax.figure); return p


# ─── 합본 (2x3) ───
def combined():
    fig = plt.figure(figsize=(20, 13))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 0.75], hspace=0.4, wspace=0.18)
    axA = fig.add_subplot(gs[0, 0]); graph_A(axA, standalone=False)
    axB = fig.add_subplot(gs[0, 1]); graph_B(axB, standalone=False)
    axC = fig.add_subplot(gs[1, 0]); graph_C(axC, standalone=False)
    # D는 2칸 (좌우 서브플롯) → gs[1,1]을 1x2로 쪼갬
    gsD = gs[1, 1].subgridspec(1, 2, wspace=0.25)
    axD1 = fig.add_subplot(gsD[0]); axD2 = fig.add_subplot(gsD[1])
    graph_D([axD1, axD2], standalone=False)
    axE = fig.add_subplot(gs[2, :]); graph_E(axE, standalone=False)
    fig.suptitle("로컬 LLM 제조 전처리 — 제한 스펙(RTX 3070 8GB) 측정 종합",
                 fontsize=22, fontweight="bold", y=0.985)
    p = f"{OUT}/graph_combined.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


if __name__ == "__main__":
    paths = [graph_A(), graph_B(), graph_C(), graph_D(), graph_E(), combined()]
    print("\n생성된 그래프:")
    for p in paths:
        sz = os.path.getsize(p) // 1024
        print(f"  {p}  ({sz} KB)")
