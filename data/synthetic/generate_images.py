"""
synthetic/generate_images.py
============================
KAMP 검사 이미지 데이터의 "구조"를 모사한 합성 더미 생성기.

⚠️ 내용은 가짜지만 형태(폴더 구조·라벨 방식·해상도/모드 분포)는 실제 KAMP와 동일하게 만든다.
   → 나중에 IMAGE_DATA_ROOT 한 줄만 실제 KAMP 경로로 바꾸면 무손실 교체 가능.

모사하는 실제 구조 (docs/archive/data_summary.txt 기준):
  - 폴더명=라벨 방식 (wafer_defect: 6클래스, vision_taping)
  - .txt 동명 페어 라벨 (welding_bead, inspection_image)
  - ★해상도 혼재 (press_aluminum 807~837, wafer_defect 1430+1184)
  - ★컬러모드 혼재 (RGB / grayscale=L / RGBA)
  - 다양한 포맷 (bmp / jpg / png)

생성 데이터셋 (data/synthetic/inspection-image/ 아래):
  1) wafer_defect/        — 6클래스 폴더=라벨, png, 해상도+RGBA 혼재 [챌린지: 폴더라벨·해상도혼재]
  2) welding_bead/        — jpg + 동명 .txt 페어, grayscale [챌린지: txt페어·대용량해상도]
  3) press_aluminum/      — 샘플/(라벨X) + 학습용/(라벨O), jpg, 사이즈변동 [챌린지: 혼합구조]
"""
from __future__ import annotations
import os
import random
from PIL import Image, ImageDraw

random.seed(42)
OUT = os.path.join(os.path.dirname(__file__), "inspection-image")


def _draw_defect(img: Image.Image, defect_type: str) -> Image.Image:
    """가짜 결함 패턴을 그린다 (스크래치/얼룩/구멍 등)."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    if defect_type == "SCRATCH":
        for _ in range(random.randint(1, 3)):
            x1, y1 = random.randint(0, w), random.randint(0, h)
            d.line([(x1, y1), (x1 + random.randint(-80, 80), y1 + random.randint(-80, 80))],
                   fill=200, width=random.randint(2, 5))
    elif defect_type == "AREA":
        x, y = random.randint(0, w - 100), random.randint(0, h - 100)
        d.ellipse([x, y, x + random.randint(30, 90), y + random.randint(30, 90)], fill=160)
    elif defect_type == "NEEDLE":
        for _ in range(random.randint(5, 15)):
            x, y = random.randint(0, w), random.randint(0, h)
            d.point([(x, y)], fill=255)
    # PASS / DISTRIBUTION / FAIL 등은 미세 노이즈만
    return img


def _make_image(size: tuple[int, int], mode: str, defect: str) -> Image.Image:
    """지정 해상도·모드의 가짜 검사 이미지."""
    base_color = random.randint(80, 140)
    if mode == "RGB":
        img = Image.new("RGB", size, (base_color, base_color, base_color))
    elif mode == "RGBA":
        img = Image.new("RGBA", size, (base_color, base_color, base_color, 255))
    else:  # L (grayscale)
        img = Image.new("L", size, base_color)
    return _draw_defect(img, defect)


def gen_wafer_defect() -> dict:
    """1) 6클래스 폴더=라벨, png. ★해상도+RGBA 혼재★ (실제 wafer_defect 모사)."""
    root = os.path.join(OUT, "wafer_defect")
    classes = ["AREA", "DISTRIBUTION", "FAIL", "NEEDLE", "PASS", "SCATCH"]
    n_per = 8  # 실제는 50, 더미는 가볍게
    count = 0
    for cls in classes:
        cdir = os.path.join(root, cls)
        os.makedirs(cdir, exist_ok=True)
        for i in range(n_per):
            # ★해상도 혼재: 대부분 1430×1380, 일부 1184×1134
            size = (1430, 1380) if random.random() > 0.3 else (1184, 1134)
            # 데모 속도 위해 실제비율 유지하되 1/4로 축소
            size = (size[0] // 4, size[1] // 4)
            img = _make_image(size, "RGBA", cls)  # ★RGBA
            # ★SCATCH만 4자리 padding (실제 챌린지)
            name = f"{i+1:04d}.png" if cls == "SCATCH" else f"{cls.lower()}_{i+1}.png"
            img.save(os.path.join(cdir, name))
            count += 1
    return {"dataset": "wafer_defect", "files": count, "classes": len(classes),
            "challenges": ["폴더명=라벨(6클래스)", "해상도 혼재", "RGBA 모드", "SCATCH 4자리 padding"]}


def gen_welding_bead() -> dict:
    """2) jpg + 동명 .txt 페어, grayscale. ★txt 페어 라벨★ (실제 welding_bead 모사)."""
    root = os.path.join(OUT, "welding_bead")
    os.makedirs(root, exist_ok=True)
    count = 0
    for i in range(20):  # 실제 554, 더미 20
        # 실제 2464×2056 grayscale → 1/4 축소
        size = (2464 // 4, 2056 // 4)
        img = _make_image(size, "L", random.choice(["SCRATCH", "PASS"]))  # ★grayscale
        # 실제 명명 패턴 모사: SL20231122_N1_114859_buff8_Ori.jpg
        stem = f"SL2024{random.randint(1000,1230):04d}_N{random.randint(1,3)}_{random.randint(100000,235959):06d}_buff{random.randint(1,9)}_Ori"
        img.save(os.path.join(root, f"{stem}.jpg"), quality=85)
        # ★동명 .txt 라벨 페어
        label = random.choice(["OK", "NG"])
        with open(os.path.join(root, f"{stem}.txt"), "w") as f:
            f.write(f"label={label}\nbbox=0,0,{size[0]},{size[1]}\n")
        count += 1
    return {"dataset": "welding_bead", "files": count * 2, "images": count,
            "challenges": ["동명 .txt 페어 라벨", "대용량 해상도", "grayscale(mode L)"]}


def gen_press_aluminum() -> dict:
    """3) 샘플/(라벨X) + 학습용/(라벨O), jpg. ★사이즈 변동 + 혼합 구조★."""
    root = os.path.join(OUT, "press_aluminum")
    # 샘플 폴더 (라벨 없음)
    sdir = os.path.join(root, "샘플")
    os.makedirs(sdir, exist_ok=True)
    for i in range(5):
        # ★사이즈 변동: 807~837 × 835~840
        size = (random.randint(807, 837) // 2, random.randint(835, 840) // 2)
        _make_image(size, "RGB", random.choice(["AREA", "PASS"])).save(
            os.path.join(sdir, f"sample_{i+1}.jpg"), quality=85)
    # 학습용 폴더 (라벨 = 하위폴더 OK/NG)
    for label in ["OK", "NG"]:
        ldir = os.path.join(root, "학습용", label)
        os.makedirs(ldir, exist_ok=True)
        for i in range(5):
            size = (random.randint(807, 837) // 2, random.randint(835, 840) // 2)
            _make_image(size, "RGB", "PASS" if label == "OK" else "SCRATCH").save(
                os.path.join(ldir, f"{label.lower()}_{i+1}.jpg"), quality=85)
    return {"dataset": "press_aluminum", "files": 15,
            "challenges": ["혼합 구조(샘플 라벨X + 학습용 라벨O)", "사이즈 변동", "RGB"]}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    results = [gen_wafer_defect(), gen_welding_bead(), gen_press_aluminum()]
    print("=" * 64)
    print("inspection-image 합성 더미 생성 완료 (KAMP 구조 모사)")
    print("=" * 64)
    for r in results:
        print(f"\n  [{r['dataset']}] 파일 {r['files']}개")
        for c in r["challenges"]:
            print(f"     - 챌린지: {c}")
    print(f"\n위치: {OUT}")


if __name__ == "__main__":
    main()
