"""검수 대시보드:  streamlit run app.py

1) 이슈 추천  2) 대본 만들기/수정  3) 렌더된 영상 검수(승인/거절)
업로드 결정은 항상 사람이 합니다. 승인된 영상은 output/approved/ 로 이동합니다.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import streamlit as st

import config
from llm import Script

st.set_page_config(page_title="쇼츠 자동화", page_icon="🎬", layout="wide")
st.title("🎬 커뮤 이슈 → 쇼츠")

tab_suggest, tab_make, tab_review = st.tabs(["① 이슈 추천", "② 대본·렌더", "③ 검수·승인"])

# ---------------- ① 이슈 추천 ----------------
with tab_suggest:
    kw = st.text_input("키워드", value="배틀그라운드", help="예: 배틀그라운드, 롤, 메이플, 유머 등")
    if st.button("후보 가져와서 AI 추천받기", type="primary"):
        from llm import rank_candidates
        from sources import google_news
        with st.spinner("뉴스 후보 수집 + 점수화 중..."):
            cands = google_news(kw)
            st.session_state.ranked = rank_candidates(cands, topic_hint=kw) if cands else []
    for i, (c, r) in enumerate(st.session_state.get("ranked", [])):
        with st.container(border=True):
            st.markdown(f"**[{r.score}] {c.title}**  \n{c.source} · {c.published}")
            st.caption(f"기획: {r.angle}  |  리스크: {r.risk}")
            cols = st.columns([1, 5])
            if cols[0].button("이걸로 만들기", key=f"pick{i}"):
                st.session_state.picked_url = c.url
                st.success("② 탭으로 이동하세요. URL이 채워져 있습니다.")
            cols[1].markdown(f"[원문 열기]({c.url})")

# ---------------- ② 대본·렌더 ----------------
with tab_make:
    st.caption("URL을 넣거나, 커뮤니티 글 본문을 직접 붙여넣으세요 (커뮤니티는 붙여넣기가 가장 확실합니다).")
    url = st.text_input("URL", value=st.session_state.get("picked_url", ""))
    pasted = st.text_area("또는 본문 붙여넣기", height=160)
    direction = st.text_input("연출 요청 (선택)", placeholder="예: 배그 유저 시점으로, 드립 많이")

    if st.button("대본 생성", type="primary"):
        from llm import make_script
        from sources import fetch_article_text
        with st.spinner("대본 작성 중..."):
            text = pasted.strip() or fetch_article_text(url)
            st.session_state.script_json = make_script(text, direction).model_dump_json(indent=2)

    up = st.file_uploader("또는 대본 JSON 불러오기", type="json")
    if up:
        st.session_state.script_json = up.read().decode("utf-8")

    if "script_json" in st.session_state:
        edited = st.text_area("대본 (직접 수정 가능)", st.session_state.script_json, height=420)
        try:
            script = Script.model_validate_json(edited)
        except Exception as e:  # noqa: BLE001
            st.error(f"JSON 형식 오류: {e}")
            script = None
        if script:
            for f in script.risk_flags:
                st.warning(f)
            silent = st.checkbox("TTS 없이 무음으로 빠르게 미리보기")
            if st.button("영상 렌더"):
                from pipeline import _slug
                from render import render
                with st.spinner("렌더 중..."):
                    out = render(script, config.DRAFT_DIR / _slug(script.title), silent=silent)
                st.success(f"완료! ③ 탭에서 검수하세요. ({out.parent.name})")

# ---------------- ③ 검수·승인 ----------------
with tab_review:
    drafts = sorted((p for p in config.DRAFT_DIR.iterdir() if (p / "final.mp4").exists()), reverse=True)
    if not drafts:
        st.info("검수 대기 중인 영상이 없습니다.")
    for d in drafts:
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            c1.video(str(d / "final.mp4"))
            with c2:
                title = st.text_input("제목", meta["title"], key=f"t{d.name}")
                desc = st.text_area("설명", meta["description"], height=140, key=f"d{d.name}")
                for f in meta.get("risk_flags", []):
                    st.warning(f)
                checked = st.checkbox("사실관계·실명/개인정보·원문 복붙 여부 확인했음", key=f"c{d.name}")
                b1, b2 = st.columns(2)
                if b1.button("✅ 승인 (업로드 대기열로)", key=f"a{d.name}", disabled=not checked):
                    meta.update(title=title, description=desc, status="approved")
                    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                    shutil.move(str(d), config.APPROVED_DIR / d.name)
                    st.rerun()
                if b2.button("🗑 거절", key=f"r{d.name}"):
                    shutil.move(str(d), config.REJECTED_DIR / d.name)
                    st.rerun()

    approved = sorted(config.APPROVED_DIR.iterdir(), reverse=True) if config.APPROVED_DIR.exists() else []
    if approved:
        st.subheader(f"업로드 대기열 ({len(approved)})")
        for d in approved:
            st.write(f"- {d.name}  →  `{d / 'final.mp4'}`")
