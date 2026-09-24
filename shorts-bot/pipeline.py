"""CLI 파이프라인.

예)
  python pipeline.py suggest "배틀그라운드"              # 이슈 후보 추천
  python pipeline.py make --url https://...             # URL → 대본 → 영상(검수 대기)
  python pipeline.py make --text-file post.txt          # 커뮤 글 본문 붙여넣은 파일 → 영상
  python pipeline.py render samples/pubg_asia_stars.json --silent   # API 없이 렌더만 테스트
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import config
from llm import Script


def _slug(title: str) -> str:
    s = re.sub(r"[^\w가-힣]+", "_", title).strip("_")[:30]
    return f"{datetime.now():%Y%m%d_%H%M%S}_{s}"


def cmd_suggest(args):
    from llm import rank_candidates
    from sources import google_news
    cands = google_news(args.keyword, limit=args.limit)
    if not cands:
        print("후보가 없습니다."); return
    for c, r in rank_candidates(cands, topic_hint=args.keyword):
        print(f"[{r.score:3d}] {c.title}\n      기획: {r.angle}\n      리스크: {r.risk}\n      {c.url}\n")


def cmd_make(args):
    from llm import make_script
    from render import render
    from sources import fetch_article_text
    if args.url:
        text = fetch_article_text(args.url)
    else:
        text = Path(args.text_file).read_text(encoding="utf-8")
    script = make_script(text, direction=args.direction or "")
    out = render(script, config.DRAFT_DIR / _slug(script.title), silent=args.silent)
    _report(script, out)


def cmd_render(args):
    from render import render
    script = Script.model_validate_json(Path(args.script).read_text(encoding="utf-8"))
    out = render(script, config.DRAFT_DIR / _slug(script.title), silent=args.silent)
    _report(script, out)


def _report(script: Script, out: Path):
    print(f"\n완성: {out}\n제목: {script.title}")
    if script.risk_flags:
        print("⚠ 검수 체크:\n  - " + "\n  - ".join(script.risk_flags))
    print("검수 후 `streamlit run app.py` 에서 승인/거절하세요.")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("suggest"); s.add_argument("keyword"); s.add_argument("--limit", type=int, default=20)
    s.set_defaults(fn=cmd_suggest)

    m = sub.add_parser("make")
    g = m.add_mutually_exclusive_group(required=True)
    g.add_argument("--url"); g.add_argument("--text-file")
    m.add_argument("--direction", help="연출 요청 (예: '배그 유저 시점으로 드립 많이')")
    m.add_argument("--silent", action="store_true", help="TTS 없이 무음으로 렌더")
    m.set_defaults(fn=cmd_make)

    r = sub.add_parser("render"); r.add_argument("script"); r.add_argument("--silent", action="store_true")
    r.set_defaults(fn=cmd_render)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
