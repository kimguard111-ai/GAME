# shorts-bot — 커뮤 이슈 → 쇼츠 반자동 제작기

유머·게임 이슈를 **추천 → 대본 → TTS → 9:16 영상 → 사람이 검수/승인**까지 자동화합니다.
업로드 여부는 항상 사람이 결정합니다. 업로드 API 연동은 다음 단계에서 붙입니다.

```
① 이슈 추천   키워드 → 구글 뉴스 RSS → Claude가 조회수 잠재력·리스크 점수화
② 대본       URL/본문 → Claude가 '재구성 + 채널 코멘트' 대본(JSON) 생성 → 직접 수정 가능
③ 렌더       edge-tts 음성 + Pillow 자막 장면 + FFmpeg → final.mp4
④ 검수       Streamlit 대시보드에서 미리보기 → 체크리스트 확인 → 승인/거절
```

## 설치 (Windows/Mac 공통)

```bash
cd shorts-bot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

- **Claude API 키**: https://console.anthropic.com 에서 발급 후 `ANTHROPIC_API_KEY` 환경변수로 설정합니다.
- **폰트**: Windows는 맑은고딕, Mac은 애플SD고딕을 자동으로 사용합니다. 더 예쁘게 하려면 [Pretendard](https://github.com/orioncactus/pretendard)의 `Pretendard-Bold.otf`를 `shorts-bot/fonts/`에 넣으세요.
- FFmpeg는 `imageio-ffmpeg`가 자동으로 포함하므로 따로 설치하지 않아도 됩니다.

## 사용법

```bash
# 대시보드 (추천)
streamlit run app.py

# CLI
python pipeline.py suggest "배틀그라운드"                      # 이슈 후보 추천
python pipeline.py make --url "https://기사주소"               # URL → 영상
python pipeline.py make --text-file post.txt --direction "배그 유저 시점, 드립 많이"
python pipeline.py render samples/pubg_asia_stars.json         # API 키 없이 샘플 대본만 렌더
```

결과물은 `output/drafts/<날짜_제목>/final.mp4`에 저장됩니다. 승인하면 `output/approved/`로 이동합니다.

## 설정 (환경변수)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `SHORTS_CHANNEL_NAME` | 오늘의 커뮤 이슈 | 영상 상단 채널명 |
| `SHORTS_VOICE` | ko-KR-InJoonNeural | edge-tts 음성 (여: ko-KR-SunHiNeural) |
| `SHORTS_VOICE_RATE` | +15% | 말하기 속도 |
| `SHORTS_MODEL` | claude-opus-5 | 대본/추천 모델 |
| `SHORTS_FONT` | 자동 탐색 | 한글 폰트 경로 |

## 수익화를 위한 운영 원칙 (중요)

- **원문 낭독 금지**: 프롬프트에서 요약·재구성과 채널 코멘트를 강제합니다. 유튜브 '재사용/반복 콘텐츠' 판정을 피하는 핵심입니다.
- **커뮤니티 크롤링 안 함**: 약관 위반과 차단 위험이 있어서, 커뮤니티 글은 URL이나 본문을 직접 넣는 방식으로만 받습니다.
- **검수 체크박스를 확인해야 승인 가능**: 사실관계, 일반인 실명/개인정보, 원문 복붙 여부를 확인해야 합니다.
- **출처 표기**: 설명란 끝에 자동으로 들어갑니다.
- 업로드는 하루 1~3개를 권장합니다. 같은 목소리·템플릿을 유지해 채널 정체성을 만드세요.

## 다음 단계 (TODO)

- [ ] YouTube Data API 업로드 (승인 폴더 → 예약 업로드)
- [ ] Instagram Reels / TikTok 업로드
- [ ] 장면별 배경 이미지 지정 (`render(..., backgrounds={0: Path(...)})` 이미 지원) + 대시보드 업로드 UI
- [ ] 단어 단위 자막 싱크 (edge-tts WordBoundary 이벤트)
- [ ] 배경음악/효과음, 줌·흔들림 모션
