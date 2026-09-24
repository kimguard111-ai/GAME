"""전역 설정. 환경변수로 덮어쓸 수 있습니다."""
import os
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT_DIR = Path(os.getenv("SHORTS_OUTPUT_DIR", ROOT / "output"))
DRAFT_DIR = OUTPUT_DIR / "drafts"        # 렌더 완료, 검수 대기
APPROVED_DIR = OUTPUT_DIR / "approved"   # 내가 승인 → 업로드 대기열
REJECTED_DIR = OUTPUT_DIR / "rejected"

MODEL = os.getenv("SHORTS_MODEL", "claude-opus-5")

# edge-tts 한국어 음성: ko-KR-InJoonNeural(남), ko-KR-SunHiNeural(여), ko-KR-HyunsuMultilingualNeural(남)
VOICE = os.getenv("SHORTS_VOICE", "ko-KR-InJoonNeural")
VOICE_RATE = os.getenv("SHORTS_VOICE_RATE", "+15%")  # 쇼츠는 약간 빠르게

WIDTH, HEIGHT = 1080, 1920
FPS = 30
CHANNEL_NAME = os.getenv("SHORTS_CHANNEL_NAME", "오늘의 커뮤 이슈")

# 한글 폰트: 환경변수 > OS별 기본 후보 순서로 탐색
_FONT_CANDIDATES = [
    os.getenv("SHORTS_FONT", ""),
    str(ROOT / "fonts" / "Pretendard-Bold.otf"),
    str(ROOT / "fonts" / "NanumGothicBold.ttf"),
    "C:/Windows/Fonts/malgunbd.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def font_path() -> str:
    for p in _FONT_CANDIDATES:
        if p and Path(p).exists():
            return p
    raise FileNotFoundError(
        "한글 폰트를 찾지 못했습니다. shorts-bot/fonts/ 에 Pretendard-Bold.otf 를 넣거나 "
        "SHORTS_FONT 환경변수로 경로를 지정하세요."
    )


for d in (DRAFT_DIR, APPROVED_DIR, REJECTED_DIR):
    d.mkdir(parents=True, exist_ok=True)
