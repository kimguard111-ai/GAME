"""대본 → 9:16 세로 영상 렌더링 (Pillow로 장면 이미지, FFmpeg로 합성)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config
from llm import Script
from tts import FFMPEG, synthesize

W, H = config.WIDTH, config.HEIGHT
ACCENT = (255, 214, 0)
GAP = 0.25  # 장면 사이 숨 고르기(초)


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(config.font_path(), size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    """어절 단위로 줄바꿈하고, 한 어절이 한 줄보다 길 때만 글자 단위로 자릅니다."""
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split():
            trial = f"{cur} {word}" if cur else word
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
                continue
            if cur:
                lines.append(cur)
            cur = ""
            for ch in word:
                if draw.textlength(cur + ch, font=font) > max_w and cur:
                    lines.append(cur); cur = ""
                cur += ch
        lines.append(cur)
    return [l for l in lines if l]


def _background(bg: Path | None) -> Image.Image:
    if bg and bg.exists():
        img = Image.open(bg).convert("RGB")
        scale = max(W / img.width, H / img.height)
        img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
        left, top = (img.width - W) // 2, (img.height - H) // 2
        img = img.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(2))
        return Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    # 기본: 세로 그라디언트
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(18 + 20 * t), int(18 + 10 * t), int(40 + 30 * t)))
    return img


def _outlined(d, xy, text, font, fill, stroke=6, anchor="mm"):
    d.text(xy, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor=anchor)


def scene_image(script: Script, idx: int, out: Path, bg: Path | None = None) -> None:
    sc = script.scenes[idx]
    img = _background(bg)
    d = ImageDraw.Draw(img)

    # 상단 훅 박스 (영상 내내 고정)
    hook_font = _font(78)
    d.rounded_rectangle([60, 170, W - 60, 330], radius=28, fill=ACCENT)
    d.text((W // 2, 250), script.hook, font=hook_font, fill=(0, 0, 0), anchor="mm")
    d.text((W // 2, 385), config.CHANNEL_NAME, font=_font(40), fill=(220, 220, 220), anchor="mm")

    # 중앙 큰 자막
    cap_font = _font(110)
    lines = _wrap(d, sc.caption, cap_font, W - 140)
    y0 = H // 2 - (len(lines) - 1) * 70
    for i, line in enumerate(lines):
        _outlined(d, (W // 2, y0 + i * 140), line, cap_font, (255, 255, 255), stroke=8)

    # 하단 내레이션 자막
    sub_font = _font(52)
    sub = _wrap(d, sc.narration, sub_font, W - 160)[:4]
    ys = H - 520
    box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle([50, ys - 50, W - 50, ys + len(sub) * 72 + 10], radius=24, fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img.convert("RGBA"), box).convert("RGB")
    d = ImageDraw.Draw(img)
    for i, line in enumerate(sub):
        d.text((W // 2, ys + i * 72), line, font=sub_font, fill=(255, 255, 255), anchor="mt")

    # 진행 바
    prog = (idx + 1) / len(script.scenes)
    d.rectangle([0, H - 14, int(W * prog), H], fill=ACCENT)
    img.save(out)


def render(script: Script, workdir: Path, silent: bool = False,
           backgrounds: dict[int, Path] | None = None) -> Path:
    """workdir 안에 scene_*.png/mp3/mp4 와 최종 final.mp4, script.json을 만듭니다."""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "script.json").write_text(script.model_dump_json(indent=2), encoding="utf-8")
    backgrounds = backgrounds or {}
    clips = []
    for i, sc in enumerate(script.scenes):
        png, mp3, mp4 = (workdir / f"scene_{i:02d}.{ext}" for ext in ("png", "mp3", "mp4"))
        scene_image(script, i, png, backgrounds.get(i))
        dur = synthesize(sc.narration, mp3, silent=silent) + GAP
        subprocess.run([
            FFMPEG, "-y", "-loglevel", "error",
            "-loop", "1", "-framerate", str(config.FPS), "-i", str(png),
            "-i", str(mp3),
            "-af", f"apad=pad_dur={GAP}", "-t", f"{dur:.2f}",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", str(config.FPS),
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
            str(mp4),
        ], check=True)
        clips.append(mp4)

    concat = workdir / "concat.txt"
    concat.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    final = workdir / "final.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(final)], check=True)

    meta = {"title": script.title, "description": script.description + "\n\n" + " ".join(script.hashtags),
            "hashtags": script.hashtags, "risk_flags": script.risk_flags, "status": "draft"}
    (workdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return final
