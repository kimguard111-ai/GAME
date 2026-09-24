"""TTS. 기본은 무료 edge-tts. 나중에 Typecast/ElevenLabs 등으로 교체하기 쉽게 함수 하나로 둡니다."""
from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

import config

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def audio_duration(path: Path) -> float:
    err = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if not m:
        raise RuntimeError(f"오디오 길이를 읽지 못했습니다: {path}")
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def _silence(out: Path, seconds: float) -> None:
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono", "-t", f"{seconds:.2f}", str(out)], check=True)


async def _edge(text: str, out: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, config.VOICE, rate=config.VOICE_RATE).save(str(out))


def synthesize(text: str, out: Path, silent: bool = False) -> float:
    """text를 out(mp3)으로 합성하고 길이(초)를 돌려줍니다.
    silent=True면 음성 없이 글자 수 기반 길이의 무음(미리보기/오프라인 테스트용)."""
    if silent:
        _silence(out, max(1.5, len(text) * 0.13))
    else:
        asyncio.run(_edge(text, out))
    return audio_duration(out)
