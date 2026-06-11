# 관광 챗봇 응답 전략 결정 기록

마지막 갱신: 2026-05-15

## 왜 남기는가

초기 engineering review에서는 `/tourism/chat`을 offline-index 기반으로 고정하는 방향을 선택했다. 이후 실제 서비스 요구와 호출량 제한을 다시 검토하면서, 현재 구현은 **cache/fallback-first + live-on-miss** 방식으로 바뀌었다.

이 문서는 나중에 품질, 쿼터, 속도, 시연 안정성을 다시 검토할 때 어느 방식으로 돌아갈지 판단하기 위한 비교 기록이다.

## 두 방식 요약

### 예정 방식: offline-index 우선

```text
TourAPI 샘플 수집
  -> Markdown 생성
  -> Chroma 재색인
  -> 사용자 질문
  -> Chroma 검색
  -> Markdown 카드 파싱
  -> 답변 반환
```

요청 시점에는 외부 TourAPI를 호출하지 않는다. 미리 수집해 둔 Markdown과 Chroma 인덱스가 사실상 응답 재료다.

### 현재 방식: cache/fallback-first + live-on-miss

```text
사용자 질문
  -> 지역/조건/확장 의도 구조화
  -> 동명이 지역이면 지역 선택 후보 반환
  -> 이전 live 조회 Markdown 캐시 확인
  -> Chroma 색인과 로컬 Markdown fallback 확인
  -> TourAPI areaBasedList2 후보 조회
  -> 상위 후보 detailCommon2 + detailWithTour2 조회
  -> TourismPlaceCard 정규화
  -> live 결과를 live_markdown에 저장
  -> 답변 반환
```

이전에 live로 조회한 같은 지역 카드가 있으면 Markdown 캐시를 먼저 사용한다. live 캐시에 없으면 Chroma 색인과 로컬 Markdown fallback을 먼저 확인한다. 그래도 같은 지역 카드가 없을 때만 요청 시점에 live TourAPI를 사용한다. 단, 저장된 후보가 5장 미만이고 live TourAPI를 사용할 수 있으면 자동 호출하지 않고 `최신 정보 더 찾기` 후속 버튼을 제공한다. 사용자가 이 버튼을 누른 경우에만 live TourAPI 후보를 보강한다. live 성공 카드는 `data/generated/tour_api/live_markdown/`에 저장하고, `data/raw/tourism_accessible/`는 계획 수집한 fallback/색인 후보로 유지한다. 데이터 신선도는 MVP 이후 주기적 갱신 배치로 보완한다.

## 핵심 차이

| 항목 | offline-index 우선 | cache/fallback-first + live-on-miss |
|---|---|---|
| 데이터 신선도 | 수집 시점에 고정 | 캐시/fallback은 수집 시점 기준, miss 때만 live |
| 지역 커버리지 | 수집한 지역/파일에 제한 | fallback miss 지역은 TourAPI로 확장 가능 |
| API 호출량 | 요청 중 0회 | cache/fallback miss 때만 후보/상세 호출 발생 |
| 응답 속도 | 빠르고 예측 가능 | 네트워크와 API 상태에 영향 |
| 장애 대응 | API 장애와 무관하게 안정 | fallback 없으면 API 장애 영향 큼 |
| 구현 복잡도 | 낮음 | 캐시 저장, 쿼터, timeout, fallback 상태 필요 |
| 테스트 난이도 | fixture 중심으로 단순 | live/mock/fallback 경로를 모두 테스트해야 함 |
| 시연 안정성 | 네트워크 영향을 덜 받음 | live 실패 시 fallback 설계가 중요 |
| 사용자 기대 | “저장된 후보 중 추천”에 가까움 | “현재 공공데이터를 조회해 추천”에 가까움 |

## offline-index 우선의 장점

- 요청 중 외부 API를 호출하지 않아 빠르고 안정적이다.
- 공모전 시연 중 네트워크, 공공데이터포털 장애, 쿼터 문제에 덜 민감하다.
- pytest와 고정 fixture로 회귀 테스트를 만들기 쉽다.
- Chroma/RAG 흐름을 명확하게 보여줄 수 있다.
- 같은 질문을 반복해도 호출 비용이 없다.

## offline-index 우선의 단점

- 수집하지 않은 지역은 답할 수 없거나 빈약하게 답한다.
- “부산 중구”, “인천 중구”, “제주”처럼 지역 조합이 넓어질수록 사전 수집 부담이 커진다.
- 사용자는 채팅으로 자유롭게 묻기 때문에, 미리 모아 둔 지역만 답하는 방식은 서비스처럼 보이기 어렵다.
- 데이터가 오래되면 실제 공공데이터와 다를 수 있다.
- 답변 품질 문제가 모델 문제가 아니라 수집 범위 문제인데도 사용자에게는 구분되지 않는다.

## cache/fallback-first + live-on-miss의 장점

- 저장된 live 캐시와 fallback을 먼저 사용해 API 호출량을 줄인다.
- 한 번 live로 조회한 지역은 Markdown 캐시를 재사용해 같은 지역 반복 호출을 줄인다.
- fallback에 없는 지역만 live로 보강해 지역 커버리지를 넓힌다.
- fallback 데이터는 전국 전체 DB가 아니라 최소 안전망만 있으면 된다.
- 동명이 지역 선택, 시군구 확장, 조건 랭킹 같은 상담 흐름과 잘 맞는다.
- 나중에 캐시를 SQLite/JSON으로 확장하면 호출량과 신선도 균형을 더 정교하게 잡을 수 있다.

## cache/fallback-first + live-on-miss의 단점

- `areaBasedList2`, `detailCommon2`, `detailWithTour2` 호출량이 누적된다.
- 공공데이터포털 일일 트래픽 제한에 직접 영향을 받는다.
- fallback miss 요청은 API 응답 시간에 묶인다.
- API timeout이나 502 같은 외부 실패가 사용자 경험에 들어올 수 있다.
- 테스트가 더 복잡하다. live 성공, live 실패, Chroma fallback, Markdown fallback, 지역 선택 경로를 모두 고정해야 한다.
- Markdown 캐시는 수동 TTL/만료 정책이 아직 없어 오래된 공공데이터를 계속 쓸 수 있다.

## 현재 방식에서 특히 조심할 점

- 오늘처럼 fallback 수집과 UI 테스트를 함께 하면 같은 날 호출량이 빠르게 늘어난다.
- 공공데이터포털 화면에서 엔드포인트별 1,000건/일이라 보여도, 운영상 서비스 단위 제한이나 지연 집계가 있을 수 있다.
- live UI를 외부 터널로 열어 두면 다른 사람이 버튼을 누르는 것만으로도 TourAPI 호출이 발생한다.
- 시연 중에는 필요하면 `TOURISM_LIVE_LOOKUP_ENABLED=false`로 live 조회를 끄고 fallback만 사용할 수 있어야 한다.
- fallback Markdown은 전체 관광 DB가 아니라 지역별 최소 안전망이다. 품질 평가는 별도로 해야 한다.

## 현재 선택

현재 선택은 **cache/fallback-first + live-on-miss**이다.

단, 무조건 live-only가 아니라 조건부 권장안이다.

| 상황 | 권장 모드 |
|---|---|
| 개발/QA/시연 전 준비 | cache/fallback-first + live-on-miss |
| 공공데이터 호출량이 불안정함 | fallback-only 또는 live 제한 |
| 시연장 네트워크가 불안함 | `TOURISM_LIVE_LOOKUP_ENABLED=false`로 끄고 fallback-only |
| 장기 운영 | cache/fallback-first + 주기적 갱신 + live-on-miss |

이유:

- 2026-06-10 전까지 앱보다 기본 서비스 완성이 우선이다.
- 사용자는 선택형 카드뿐 아니라 자유 채팅으로 지역과 조건을 입력한다.
- 전국 모든 장소를 미리 쌓는 방식은 시간과 호출량 대비 효율이 낮다.
- 지역별 fallback은 최소 안전망으로 충분하고, 부족한 지역만 live 조회로 보강하는 편이 호출량 대비 효율적이다.

최종 권장 구조:

```text
1. 질문 구조화
2. 이전 live 조회 Markdown 캐시 확인
3. Chroma 색인과 로컬 Markdown fallback 확인
4. 그래도 없으면 live TourAPI 조회
5. 저장 후보가 5장 미만이면 `최신 정보 더 찾기` 후속 버튼 제공
6. 사용자가 `최신 정보 더 찾기`를 누르면 live TourAPI로 보강
7. 결과를 TourismPlaceCard로 카드화
8. 결과를 live_markdown에 저장
```

offline-index 우선은 폐기할 방식이 아니라 **비상/시연 안정 모드**로 남긴다.

## LLM 추론 보조 사용 기준

현재 응답 전략은 LLM이 모든 것을 판단하는 일반 챗봇 방식이 아니다. 데이터 조회와 카드 생성은 가능한 한 결정론적으로 처리하고, LLM 추론 보조는 규칙/API/RAG만으로 사용자 의도를 충분히 설명하기 어려운 순간에 제한적으로 사용한다.

용어를 구분한다.

- **추론 보조**: 후보 카드 생성 후 LLM 프롬프트로 복합 의도를 재해석하고 재랭킹하는 단계.
- **Ollama native thinking**: `think=true`를 전달했을 때 모델이 별도 thinking 필드를 반환하는 기능.

현재 프로젝트 기본 모델 `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL`는 Gemma 4 기반 모델이지만, 로컬 Ollama 확인 기준 native thinking을 지원하지 않는다. 따라서 기본 구현은 짧은 추론 보조 프롬프트로 시작한다. 2026-05-15 1차 벤치마크에서는 공식 `gemma4:e4b`와 `huihui_ai/gemma-4-abliterated:e4b`가 native thinking을 반환했지만 30초 이상 지연됐고, `qwen3:4b`는 JSON/한국어 계약을 지키지 못했다. MVP 기본값은 `think=false`로 유지한다.

추론 보조 없이 처리할 것:

- 명확한 지역과 시군구 매칭
- 명확한 접근성 조건 추출
- 동명이 지역 clarification
- cache, Chroma, Markdown fallback, live TourAPI 조회 순서
- 카드 부족 안내, fallback/degraded 진단, 범위 밖 질문 처리

추론 보조가 필요한 시점:

- 복합 사용자 상황: `휠체어를 탄 아버지`, `아이 동반`, `너무 붐비지 않는 곳`, `실내 위주`가 한 질문에 섞이는 경우
- 상황형 표현: `오래 걷기 힘든 분`, `비 오면 이동하기 편한 곳`, `쉬기 좋은 곳`
- 생활권/거리 표현: `서울역에서 멀지 않은 곳`, `해운대 근처`, `바닷가 말고 조용한 곳`
- 후보가 너무 많거나 너무 적어 재질문, 조건 완화, 지역 확장 제안이 필요한 경우
- 잘못된 전제를 설명해야 하는 경우: `강남구 바닷가`처럼 질문 자체의 전제가 데이터와 맞지 않는 경우

역할 경계:

| 단계 | 담당 |
|---|---|
| 지역/조건 1차 구조화 | 규칙 기반 파서 |
| 근거 데이터 수집 | live Markdown cache, Chroma, raw Markdown fallback, TourAPI |
| 카드 생성 | `TourismNormalizer`, `TourismPlaceCard` schema |
| 후보 재랭킹/상담 문장 | 필요할 때만 LLM 추론 보조 |
| 없는 정보 처리 | 추측 금지, `확인 필요` 또는 부족 안내 |

즉, LLM 추론 보조는 **데이터를 찾는 주체가 아니라 확인된 후보를 사용자 상황에 맞게 판단하고 설명하는 보조 계층**이다.

## 되돌림 기준

다음 조건 중 하나가 반복되면 offline-index 우선 방식으로 되돌리는 것을 검토한다.

- 하루 1,000건 제한 때문에 QA나 시연 중 live 조회를 안정적으로 유지하기 어렵다.
- live 응답 시간이 사용자 체감상 너무 느리다.
- 공공데이터포털 timeout/502가 자주 발생한다.
- live 결과 품질이 수집 fallback보다 낮거나, 음식점/비관광 후보가 과하게 섞인다.
- 심사/시연 환경에서 외부 API 호출이 불가능하거나 불안정하다.

## 되돌릴 때 해야 할 일

1. `.env`에 `TOURISM_LIVE_LOOKUP_ENABLED=false`를 둔다.
2. `/tourism/chat`의 기본 설명을 offline-index 우선으로 되돌린다.
3. `/tourism-ui/` 상태 문구를 `색인 응답` 중심으로 수정한다.
4. fallback Markdown 수집 배치를 더 넓히고 `scripts/rebuild_index.py`를 실행한다.
5. `lookup_mode=live`를 기대하는 테스트를 offline-index 기대값으로 수정한다.
6. README, GOAL, MVP plan, progress 문서를 offline-index 기준으로 다시 갱신한다.

## 현재 후속 과제

- Markdown live 캐시에 TTL/만료 정책을 둘지 검토한다.
- Post-MVP 주기적 TourAPI 갱신 배치와 재색인 절차를 설계한다.
- `lookup_mode`별 응답 품질을 20문항 eval에 포함한다.
- 추론 보조 사용 여부를 응답 이벤트 로그에 남길지 검토한다.
- 복합 상황형 질문을 eval에 추가해 규칙 기반 처리와 LLM 추론 보조 경계가 실제로 맞는지 확인한다.
- 한국어 맥락 품질이 좋은 Gemma 4 계열은 유지 후보로 두되, native thinking 필요성은 공식 `gemma4:e4b`와 Qwen/DeepSeek 계열을 실제 응답 시간과 품질로 비교한 뒤 결정한다.
- live 결과가 음식점 위주로 치우치는지 확인하고, 관광지 content type 또는 키워드 필터가 필요한지 검토한다.
- 외부 터널 시연 중 live 호출을 켤지, fallback-only로 둘지 데모 전에 결정한다.
- fallback 수집 스크립트는 live Markdown 캐시와 fallback raw에 이미 있는 `콘텐츠ID`를 중복 수집하지 않는다.
- 질문, lookup_mode, 카드 노출 순위, content_id를 연결하는 응답 이벤트 로그는 `data/generated/tour_api/query_card_events.jsonl`에 JSONL로 저장한다.
- JSONL 로그 분석은 `notebooks/tourism_event_log_analysis.ipynb`에서 수행한다. matplotlib 차트와 한글 폰트 설정을 포함한다.
- 이벤트 로그 분석이 많아지면 Post-MVP에서 SQLite로 흡수한다.
