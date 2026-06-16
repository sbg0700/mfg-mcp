"""scripts/ppt_slides.py — 발표용 3슬라이드 (승·전·결). 두 누락 보완판.

누락① 보완: 슬라이드1 시간그래프에 e4b before/after 둘 다 → "워밍업 후 빠름" 노출.
누락② 보완: 슬라이드2 하단에 VRAM 적재 메커니즘 다이어그램 → "왜 e4b만 워밍업이 듣나".

ppt_graphs.py의 graph_B/graph_C/graph_E + 상수 재사용. 스타일/데이터/폰트 동일.
"""
from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "ppt_graphs", os.path.join(os.path.dirname(__file__), "ppt_graphs.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

OUT = "scripts/ppt_assets"
os.makedirs(OUT, exist_ok=True)

C_E4B = G.C_E4B      # blue
C_26B = G.C_26B      # orange
C_COLD = "#94a3b8"   # gray (before/cold)
C_CPU = "#fca5a5"    # light red (CPU 오프로딩 영역)
C_GOOD = G.C_GOOD
C_BAD = G.C_BAD


# ─────────────────────────────────────────────────────────────────────────
# 슬라이드 1 좌측 — 시간: e4b before/after + 26b (log y)
# ─────────────────────────────────────────────────────────────────────────
def _time_before_after(ax):
    x = range(len(G.DS_ORDER))
    w = 0.2
    e_cold = [float(G.COLD[("gemma4:e4b", d)]["total_s"]) for d in G.DS_ORDER]
    e_warm = [float(G.WARM[("gemma4:e4b", d)]["total_s"]) for d in G.DS_ORDER]
    m_warm = [float(G.WARM[("gemma4:26b", d)]["total_s"]) for d in G.DS_ORDER]
    b0 = ax.bar([i - w for i in x], e_cold, w, label="e4b 콜드", color=C_COLD)
    b1 = ax.bar([i for i in x], e_warm, w, label="e4b 워밍업 후", color=C_E4B)
    b2 = ax.bar([i + w for i in x], m_warm, w, label="26b (워밍업 후)", color=C_26B)
    for bars, fmt in ((b0, "{:.1f}"), (b1, "{:.1f}"), (b2, "{:.0f}")):
        for b in bars:
            h = b.get_height()
            ax.annotate(fmt.format(h), (b.get_x() + b.get_width() / 2, h),
                        ha="center", va="bottom", fontsize=8.5, fontweight="bold",
                        xytext=(0, 1.5), textcoords="offset points")
    ax.set_yscale("log")
    ax.set_xticks(list(x))
    ax.set_xticklabels([G.DS_LABELS[d] for d in G.DS_ORDER], fontsize=10)
    ax.set_ylabel("총 추론 시간 (초, 로그)")
    ax.set_title("추론 시간 — e4b는 워밍업 후 5~7초, 26b는 125~240초", fontsize=13)
    ax.legend(loc="upper center", ncol=3, fontsize=9, framealpha=0.9)
    ax.set_ylim(2, 600)
    # e4b 워밍업 효과 강조 — 막대 사이 빈 공간 + 흰 배경 박스(가독성)
    ax.annotate(f"워밍업 후 확 줄어듦\n(콜드 {e_cold[1]:.1f}초에서 워밍 {e_warm[1]:.1f}초로)",
                xy=(1, e_warm[1]), xytext=(0.35, 42),
                fontsize=10, fontweight="bold", color="#1e293b", ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.92,
                          edgecolor=C_E4B, lw=1.3),
                arrowprops=dict(arrowstyle="->", color=C_E4B, lw=1.8))


def slide_1():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 6))
    _time_before_after(axL)
    G.graph_B(axR, standalone=False)
    axR.set_title("VRAM 사용량 — 26b는 8GB 한계 초과 + CPU 분산", fontsize=13)
    fig.suptitle("측정 — 제한 스펙(8GB)에서 두 모델", fontsize=19, fontweight="bold", y=0.99)
    G.caption(fig, "e4b는 워밍업하면 5~7초로 빨라짐(좌). 26b는 8GB 초과로 느림 유지(우).", y=0.02)
    fig.subplots_adjust(bottom=0.16, top=0.85, wspace=0.22, left=0.07, right=0.97)
    p = f"{OUT}/slide_1_measure.png"
    fig.savefig(p, dpi=170); plt.close(fig)
    return p


# ─────────────────────────────────────────────────────────────────────────
# 슬라이드 2 하단 — VRAM 적재 메커니즘 (왜 e4b만 워밍업이 듣나)
# 8GB 박스 안에 모델 적재 stacked: GPU(아래) + CPU 오프로딩(8GB 위로 넘침)
# ─────────────────────────────────────────────────────────────────────────
def _mechanism(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 21)
    ax.axis("off")
    LIMIT = 8.0  # 8GB

    def model_stack(cx, gpu_gb, cpu_gb, color_gpu, label, fits):
        bw = 1.6
        # GPU 영역 (8GB 박스 안)
        ax.add_patch(Rectangle((cx - bw / 2, 0), bw, gpu_gb, facecolor=color_gpu,
                               edgecolor="white", lw=1))
        ax.text(cx, gpu_gb / 2, f"GPU\n{gpu_gb:.1f}GB", ha="center", va="center",
                fontsize=9, fontweight="bold", color="white")
        # CPU 오프로딩 영역 (8GB 위로)
        if cpu_gb > 0:
            ax.add_patch(Rectangle((cx - bw / 2, gpu_gb), bw, cpu_gb, facecolor=C_CPU,
                                   edgecolor="white", lw=1, hatch="///"))
            ax.text(cx, gpu_gb + cpu_gb / 2, f"CPU 오프로딩\n{cpu_gb:.0f}GB",
                    ha="center", va="center", fontsize=9, fontweight="bold", color="#7f1d1d")
        ax.text(cx, -0.9, label, ha="center", va="top", fontsize=11, fontweight="bold")
        # 적합 표시
        tag = "8GB 안에 다 들어감" if fits else "8GB 넘침: CPU로 분산"
        tcol = C_GOOD if fits else C_BAD
        ax.text(cx, gpu_gb + cpu_gb + 0.6, tag, ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=tcol)

    # e4b: GPU 3.5, CPU 0 (완전 적재)
    model_stack(2.3, 3.5, 0, C_E4B, "gemma4:e4b (3.5GB)", fits=True)
    # 26b: GPU 7, CPU 12 (19GB 모델, 8GB 초과)
    model_stack(6.0, 7.0, 12.0, C_26B, "gemma4:26b (19GB)", fits=False)

    # 8GB 한계선 (라벨은 좌측 e4b 막대 위 빈 공간 — 26b 막대 겹침 회피)
    ax.axhline(LIMIT, color=G.C_LIMIT, ls="--", lw=2, xmin=0.05, xmax=0.72)
    ax.text(0.6, LIMIT + 0.35, "RTX 3070 — 8GB 한계", color=G.C_LIMIT, fontsize=10.5,
            fontweight="bold", va="bottom", ha="left")

    # 우측 결과 텍스트 (왜 e4b만 듣나) — 특수문자 없이 평이하게
    ax.text(8.5, 15, "워밍업(메모리에 미리 올림) 효과", fontsize=11, fontweight="bold",
            ha="left", color="#1e293b")
    ax.text(8.5, 12,
            "e4b: 메모리에 다 들어감\n로딩만 미리 하면 끝\n빨라짐 (33% 단축, 안정)",
            fontsize=10, ha="left", va="top", color=C_GOOD, fontweight="bold")
    ax.text(8.5, 5.8,
            "26b: 메모리 초과로 CPU 분산\n매 연산마다 CPU-GPU 왕복\n느리고 들쭉날쭉 (워밍업 무력)",
            fontsize=10, ha="left", va="top", color=C_BAD, fontweight="bold")
    ax.set_title("2. 왜 같은 워밍업인데 e4b만 빨라지나 — 메모리 적재 차이",
                 fontsize=14, fontweight="bold", pad=12)


def slide_2():
    fig = plt.figure(figsize=(13, 11.5))
    gs = fig.add_gridspec(2, 1, height_ratios=[0.9, 1.18], hspace=0.26,
                          top=0.90, bottom=0.06, left=0.09, right=0.95)
    axTop = fig.add_subplot(gs[0])
    G.graph_C(axTop, standalone=False)
    axTop.set_title("1. 병목 발견 — 데이터 크기와 무관하게 시간이 정해짐 (LLM이 병목)",
                    fontsize=14)
    axBot = fig.add_subplot(gs[1])
    _mechanism(axBot)
    fig.suptitle("병목은 LLM — 그리고 왜 e4b만 최적화가 듣는가",
                 fontsize=19, fontweight="bold", y=0.975)
    G.caption(fig, "e4b는 VRAM 완전적재라 워밍업 실효(33% 단축). "
                   "26b는 CPU 오프로딩이 구조적 병목이라 워밍업 무력 — 8GB로 26b는 안정화 불가.", y=0.018)
    p = f"{OUT}/slide_2_bottleneck.png"
    fig.savefig(p, dpi=170); plt.close(fig)
    return p


# ─────────────────────────────────────────────────────────────────────────
# 슬라이드 3 — 결론: "모델 크기 vs VRAM" 표(19GB 명시) + 메시지 3줄
# ─────────────────────────────────────────────────────────────────────────
def _summary_table(ax):
    ax.axis("off")
    cols = ["", "모델 크기", "실제 VRAM 사용", "8GB 수용", "워밍업 효과", "결론"]
    e4b = ["gemma4:e4b", "3.5 GB", "VRAM 3.5 GB", "완전 적재", "33% 개선", "제한 공장 도입 가능"]
    m26 = ["gemma4:26b", "19 GB", "GPU 7GB + CPU 12GB", "8GB 초과(CPU 분산)", "불안정", "24GB+ GPU 전제"]
    t = ax.table(cellText=[e4b, m26], colLabels=cols, cellLoc="center", loc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(11.5)
    t.scale(1, 2.5)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor("#cbd5e1")
        if r == 0:
            cell.set_facecolor("#1e293b"); cell.set_text_props(color="white", fontweight="bold")
        elif r == 1:
            cell.set_facecolor("#dcfce7" if c in (3, 5) else "#f0fdf4")
            if c in (3, 5): cell.set_text_props(color=C_GOOD, fontweight="bold")
        elif r == 2:
            cell.set_facecolor("#fee2e2" if c in (1, 3, 5) else "#fef2f2")
            if c in (1, 3, 5): cell.set_text_props(color=C_BAD, fontweight="bold")
        if c == 0: cell.set_text_props(fontweight="bold")


def slide_3():
    fig = plt.figure(figsize=(13, 7))
    ax = fig.add_axes([0.04, 0.42, 0.92, 0.34])   # 표를 화면 중앙
    _summary_table(ax)
    fig.suptitle("결론 — 제한 스펙(8GB)에선 e4b + keep-alive가 정답",
                 fontsize=18, fontweight="bold", y=0.92)
    # 핵심 메시지 3줄 (표 아래)
    msgs = [
        ("• 제한 스펙(8GB) 공장: e4b + keep-alive로 즉시 도입 가능 (10초 내 처리)", "#1e293b", 13),
        ("• 8GB 한계는 '극복'이 아니라 '맞는 모델 선택'으로 푼다", "#1e293b", 13),
        ("• 확장: 고스펙 운영은 26b, 컨테이너 배포(b2)로 스케일", "#475569", 12.5),
    ]
    y = 0.30
    for txt, col, fs in msgs:
        fig.text(0.10, y, txt, ha="left", fontsize=fs, fontweight="bold", color=col)
        y -= 0.075
    # 26b "19GB" 강조 부연
    fig.text(0.10, 0.05,
             "* 26b는 모델이 19GB라 8GB VRAM에 다 못 올라감 — GPU 7GB만 쓰고 나머지 12GB는 CPU로 분산(느림).",
             ha="left", fontsize=10, style="italic", color="#7f1d1d")
    p = f"{OUT}/slide_3_conclusion.png"
    fig.savefig(p, dpi=170); plt.close(fig)
    return p


if __name__ == "__main__":
    paths = [slide_1(), slide_2(), slide_3()]
    print("\n생성된 슬라이드:")
    for p in paths:
        print(f"  {p}  ({os.path.getsize(p)//1024} KB)")
