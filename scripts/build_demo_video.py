"""180-second captioned replay of saved evidence, explicitly not a UI recording."""

import json, sys, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".media-runtime"))
import imageio_ffmpeg

OUT = ROOT / "output/video"
OUT.mkdir(parents=True, exist_ok=True)
frames = ROOT / "tmp/video-frames"
frames.mkdir(parents=True, exist_ok=True)
F = "C:/Windows/Fonts/malgun.ttf"
B = "C:/Windows/Fonts/malgunbd.ttf"
font = lambda size, b=False: ImageFont.truetype(B if b else F, size)
FG = "#e8f0e9"
MUTED = "#a1b1a8"
LIME = "#b6ed64"
DARK = "#0b1410"
report = json.loads((ROOT / "artifacts/eval-dc5a773edccd641d/report.json").read_text())
workflow = json.loads((ROOT / "artifacts/workflow-evidence.json").read_text())
live = json.loads((ROOT / "artifacts/live-evidence.json").read_text())
labels = ["주문 확인", "반품 수령", "정책 조회", "견적 생성", "환불 확정", "DB 검증"]
sections = [
    (
        "SkillForge",
        "실행 기록에서 배우는 안전한 업무 자동화",
        [
            "반복 요청을 매번 처음부터 추론하는 부담",
            "성공한 실행 기록에서 절차 후보를 유도",
            "별도 검증과 운영자 활성화 후 재사용",
            "합성 주문 · 실제 결제 없음",
        ],
    ),
    (
        "실제 Nemotron 실행",
        "공개 도구 호출과 DB 상태를 함께 확인",
        [
            "model: nvidia/nemotron-3-super-120b-a12b",
            "run: " + live["result"]["run_id"],
            "업무 도구 6회 · 독립 oracle 통과",
            "단일 실행 사례이며 평균 성능이 아닙니다.",
        ],
    ),
    (
        "기록 → 후보 → 검증",
        "독립 성공 사례 5건, Validation 30건",
        [
            workflow["id"],
            "출처: live / 과거 주문 ID를 상수로 복사하지 않음",
            "동일한 도구 순서 + 입력·이전 출력 참조",
            "검증된 artifact hash와 현재 정책을 확인",
        ],
    ),
    (
        "정책 경계는 그대로",
        "공통 gateway로 쓰기를 검증",
        [
            "47개 회귀 테스트가 통과한 시점의 증거",
            "500,000원 이상: 운영자 단회 승인",
            "소유권·반품 수령·중복·최신 상태 검사",
            "쓰기 후 오류: 보류, 조회·조정 후 재개",
        ],
    ),
    (
        "같은 40건, 세 가지 경로",
        "실측 결과와 실패를 함께 공개",
        [
            "A ReAct: 34 / 40 · 모델 호출 244회",
            "B 수동 workflow: 40 / 40 · 모델 호출 0회",
            "C 생성 workflow: 40 / 40 · 모델 호출 0회",
            "세 경로 모두 unsafe commit 0건",
        ],
    ),
    (
        "범위와 다음 단계",
        "재현 가능한 증거를 남깁니다.",
        [
            "in-memory SQLite executor 비교 · 각 군 1회 반복",
            "자연어 router·실결제·운영자 대기 비용 제외",
            "OpenShell 격리와 대회 Skill API 세부 요건 미확정",
            "GitHub·영상 공개 URL은 사용자 확정 후 반영",
        ],
    ),
]


def wrap(draw, text, width, f):
    lines = []
    cur = ""
    for char in text:
        if draw.textlength(cur + char, font=f) > width:
            lines.append(cur)
            cur = char
        else:
            cur += char
    if cur:
        lines.append(cur)
    return lines


for section, (title, subtitle, lines) in enumerate(sections):
    for step in range(6):
        im = Image.new("RGB", (1280, 720), DARK)
        d = ImageDraw.Draw(im)
        d.text((66, 38), "TRACE MAKERS / SKILLFORGE", font=font(17, True), fill=LIME)
        d.text((66, 92), title, font=font(46, True), fill=FG)
        d.text((66, 157), subtitle, font=font(24), fill=MUTED)
        if section in {0, 1}:
            for i, label in enumerate(labels):
                x = 66 + i * 195
                y = 235
                d.rounded_rectangle(
                    (x, y, x + 180, y + 85),
                    radius=10,
                    fill="#253921" if i <= step else "#15211b",
                    outline=LIME if i == step else "#344336",
                    width=2,
                )
                d.text((x + 16, y + 13), f"{i+1:02}", font=font(15, True), fill=LIME)
                d.text((x + 16, y + 42), label, font=font(20, True), fill=FG)
            y = 362
        else:
            y = 237
        for line in lines:
            for part in wrap(d, line, 1130, font(24)):
                d.text((70, y), part, font=font(24), fill=FG)
                y += 36
            y += 15
        if section == 4:
            d.text(
                (70, 500),
                "A 실패: provider HTTP 500 5건 + 견적 참조 오류 1건",
                font=font(20),
                fill="#efc76c",
            )
            d.text(
                (70, 536),
                "수동 자동화보다 빠르다는 주장은 하지 않습니다.",
                font=font(20),
                fill=MUTED,
            )
        d.line((66, 620, 1214, 620), fill="#344336", width=1)
        d.text(
            (66, 641),
            "실제 실행 결과를 시각화한 재생 자료 · 브라우저 화면 녹화 아님",
            font=font(17),
            fill=MUTED,
        )
        position = section * 6 + step + 1
        d.rectangle((0, 707, int(1280 * position / 36), 720), fill=LIME)
        d.text((1115, 38), f"{section+1:02} / 06", font=font(18), fill=MUTED)
        im.save(frames / f"{position:02}.png")
manifest = frames / "concat.txt"
manifest.write_text(
    "".join(f"file '{i:02}.png'\nduration 5\n" for i in range(1, 37))
    + "file '36.png'\n",
    encoding="utf-8",
)
video = OUT / "SkillForge-evidence-walkthrough.mp4"
subprocess.run(
    [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(manifest),
        "-t",
        "180",
        "-vf",
        "fps=24",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(video),
    ],
    check=True,
)
reader = imageio_ffmpeg.read_frames(str(video))
meta = next(reader)
reader.close()
assert 179.9 <= meta["duration"] <= 180.1
(OUT / "video-manifest.json").write_text(
    json.dumps(
        {
            "duration_seconds": meta["duration"],
            "size": meta["size"],
            "format": "captioned evidence replay",
            "not_browser_recording": True,
            "source_evaluation": report["id"],
            "source_live_run": live["result"]["run_id"],
        },
        indent=2,
    )
)
print(
    json.dumps(
        {
            "video": str(video),
            "duration": meta["duration"],
            "bytes": video.stat().st_size,
        }
    )
)
