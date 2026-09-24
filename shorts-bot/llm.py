"""Claude로 후보 추천(점수화)과 쇼츠 대본 생성을 합니다."""
from __future__ import annotations

import anthropic
from pydantic import BaseModel, Field

import config
from sources import Candidate

_client = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client

# 정책상 거절되면 서버가 다른 모델로 자동 재시도하도록 opt-in
_FALLBACK = dict(
    extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
    extra_body={"fallbacks": "default"},
)


class RankedItem(BaseModel):
    index: int = Field(description="입력 후보 번호")
    score: int = Field(description="0~100, 쇼츠 조회수 잠재력")
    angle: str = Field(description="쇼츠로 만들 때의 한 줄 기획 각도")
    risk: str = Field(description="저작권/명예훼손/사실확인 리스크 한 줄. 없으면 '낮음'")


class Ranking(BaseModel):
    items: list[RankedItem]


class Scene(BaseModel):
    narration: str = Field(description="TTS가 읽을 문장. 1~2문장, 구어체")
    caption: str = Field(description="화면 큰 자막. 15자 내외 핵심 문구")
    visual_hint: str = Field(description="이 장면에 어울리는 배경 이미지/영상 설명(직접 준비용)")


class Script(BaseModel):
    title: str = Field(description="업로드 제목. 40자 이내, 호기심 유발, 낚시성 과장 금지")
    hook: str = Field(description="첫 2초 화면 상단 고정 문구. 12자 내외")
    scenes: list[Scene] = Field(description="5~8개 장면. 전체 낭독 40~55초 분량")
    description: str = Field(description="영상 설명란. 출처 표기 포함")
    hashtags: list[str] = Field(description="#포함 해시태그 5~8개")
    risk_flags: list[str] = Field(description="검수자가 확인해야 할 점: 실명/개인정보/미확인 주장/원문 인용 등. 없으면 빈 배열")


RANK_SYSTEM = """너는 한국 유머·게임·사회 이슈 쇼츠 채널의 기획 PD다.
후보 헤드라인들을 보고 쇼츠(60초 이하)로 만들었을 때 조회수 잠재력을 평가한다.
기준: 화제성, 감정 반응(웃김/분노/공감), 짧게 설명 가능한지, 댓글 유도력.
실명 개인 비방이나 미확인 루머가 핵심인 소재는 점수를 낮추고 risk에 적는다."""

SCRIPT_SYSTEM = """너는 한국 쇼츠 채널 '{channel}'의 대본 작가다.
입력된 커뮤니티 글/기사를 바탕으로 '원문 낭독'이 아닌 **재구성된 해설형 쇼츠 대본**을 쓴다.

규칙:
- 원문 문장을 그대로 옮기지 말고 요약·재구성한다. 짧은 인용이 필요하면 따옴표 1회 이내.
- 첫 장면은 3초 안에 궁금증을 만드는 훅.
- 중간에 채널의 관점/코멘트(드립 포함)를 최소 1회 넣는다. 이게 이 채널의 오리지널리티다.
- 마지막 장면은 시청자 의견을 묻는 질문으로 끝내 댓글을 유도한다.
- 사실과 의견을 구분한다. 확인되지 않은 내용은 '~라는 주장이 나왔다'처럼 쓴다.
- 일반인의 실명·닉네임·얼굴·개인정보는 쓰지 않는다. 공인/기업은 사실 범위 안에서만.
- 욕설·혐오 표현 금지. 가벼운 드립은 환영.
- 국가·민족·성별 갈등이 얽힌 소재는 특정 집단 전체를 싸잡는 표현을 쓰지 말고, 비판 대상을 '행위'와 '운영'으로 한정한다.
  마지막 질문도 집단 대결 구도(예: 한국 vs ○○)가 아니라 사안 자체에 대한 의견을 묻는다.
- description 끝에 '출처: <원문 제목 또는 매체명>'을 넣는다."""


def _check(resp) -> None:
    if resp.stop_reason == "refusal":
        raise RuntimeError("모델이 이 소재의 처리를 거절했습니다. 다른 소재를 고르세요.")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("응답이 잘렸습니다. 입력을 줄여 다시 시도하세요.")


def rank_candidates(cands: list[Candidate], topic_hint: str = "") -> list[tuple[Candidate, RankedItem]]:
    lines = [f"{i}. [{c.source}] {c.title} — {c.summary[:120]}" for i, c in enumerate(cands)]
    resp = client().messages.parse(
        model=config.MODEL,
        max_tokens=8000,
        system=RANK_SYSTEM,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": f"채널 방향: {topic_hint or '유머·게임·이슈'}\n\n후보:\n" + "\n".join(lines)}],
        output_format=Ranking,
        **_FALLBACK,
    )
    _check(resp)
    ranked = [(cands[r.index], r) for r in resp.parsed_output.items if 0 <= r.index < len(cands)]
    return sorted(ranked, key=lambda x: x[1].score, reverse=True)


def make_script(source_text: str, direction: str = "") -> Script:
    resp = client().messages.parse(
        model=config.MODEL,
        max_tokens=16000,
        system=SCRIPT_SYSTEM.format(channel=config.CHANNEL_NAME),
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": f"추가 연출 요청: {direction or '없음'}\n\n<source>\n{source_text}\n</source>"}],
        output_format=Script,
        **_FALLBACK,
    )
    _check(resp)
    return resp.parsed_output
