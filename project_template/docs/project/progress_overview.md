# 무장애 관광 챗봇 진행도

마지막 갱신: 2026-05-27

이 문서는 `docs/project/GOAL.md`, `docs/tourism/accessible_tourism_mvp_plan.md`, `README.md`, `TODOS.md` 기준으로 현재 MVP 진행 상태를 빠르게 보기 위한 요약이다.
응답 전략 변경 이력은 `docs/tourism/tourism_response_strategy_decision.md`에 별도로 기록한다.

## 전체 진행도

```text
MVP 전체              [████████░░] 84%
Backend contract     [█████████░] 92%
Live API coverage    [████████░░] 78%
Data/sample coverage [█████████░] 88%
MVP fallback collect [█████████░] 90%
Sigungu fallback     [███████░░░] 69%
Region alias data    [█████████░] 86%
Web demo UI          [█████████░] 90%
Quality/eval         [█████████░] 90%
Production readiness [██░░░░░░░░] 20%
```

현재 상태는 **live 캐시/색인/fallback 우선 + live TourAPI on miss + 웹/Flutter 확인 UI 병행** 단계다.
웹 UI 재QA는 40/40 통과했고 TOP_K=40 적용 후 challenge/residual hard 평가는 실패 0건이다. Flutter 앱은 최신 백엔드 계약과 live update 상태를 수용하도록 동기화했다. 공개 데모 품질로 올리기 전 남은 작업은 수동 표본 검토보다 자동 회귀 평가, 희소 접근성 데이터 보강 후보 정리, 문맥 영향 eval 관리, 문서 고정에 집중한다.

## 영역별 상태

| 영역 | 진행도 | 상태 | 근거 |
|---|---:|---|---|
| TourAPI 연결 | 92% | 동작 | `KorWithService2` live 후보 조회, 지역 코드 캐시, 엔드포인트별 일일 사용량 가드, raw SQLite 응답 캐시 |
| live 후보 조회 | 80% | 동작 | 캐시/색인/fallback miss 또는 사용자가 `최신 정보 더 찾기`를 누를 때 TourAPI 후보와 접근성 상세를 카드화, 프로세스 캐시와 SQLite raw response cache 사용 |
| 샘플 데이터 | 93% | fallback + QA 도구 | 904개 Markdown fallback + curated fallback, 샘플 감사 스크립트 추가 |
| MVP fallback 수집 | 95% | 최소 안전망 확보 | `mvp`, `fallback-1`, `fallback-2`, `fallback-3` 완료, 이후 시군구/서귀포시 보강까지 904개 Markdown 확보 |
| 시군구 fallback 확장 | 97% | 대부분 확보 | TourAPI 지역 코드 234개 중 228개 시군구가 3장 이상 확보, 0장/1장 지역은 행정구역 유효성 확인 필요 |
| 지역명 매칭 데이터 | 86% | 생성 및 파싱 연결 | 행안부 `jscode20260325` 기반 `admin_region_aliases.json` 생성, 생활권/일반구/행정동 예외 입력 테스트 확장 |
| RAG 색인 | 90% | fallback | 905개 문서/914개 청크를 Chroma에서 검색 |
| `/tourism/chat` API | 96% | 대화 흐름 보강 | cache/fallback 우선, 안전한 오류, degraded fallback, 모호 지역 선택, 시군구 확장, 조건별 카드 랭킹/근거 문장, 세션 후속 질문 반영 |
| 카드 응답 schema | 88% | 동작 | `TourismPlaceCard[]`, `sources`, `warnings`, `suggested_messages`, `reasoning_assist_used` 반환 |
| 웹 확인 UI | 90% | 앱형 시연 가능 | `/tourism-ui/`, 개발/릴리즈 모드 분리, 앱형 채팅 UI, 사용자 질문 말풍선, 타이핑/토스트 피드백, 카드 상세, 지도 검색 |
| Flutter 앱 | 80% | 별도 repo 동기화 완료 | `cheng80/chatbot_rag_app`에 최신 백엔드 계약, live update 상태, 단색 지도 아이콘, 실행 문서를 반영하고 iOS Simulator 스모크를 확인 |
| 테스트 | 95% | 주요 회귀 커버 | `pytest` 통과, 551건 자동 eval과 backend 정책/수집/감사/지역명 매칭/대화 흐름 중심 |
| 모델 품질 평가 | 97% | 대화 챌린지 + intent/context shadow classifier | 100/30/50 기존 eval과 274/97 신규 확장 eval을 합친 551건이 fallback-only/live-enabled 모두 자동 채점 실패 0건, change/replace 실사용 멀티턴 판단셋 201/201 통과, adversarial chat holdout 42/42 통과, AI Hub 추출 발화 포함 16,254 rows 의도 분류 모델 내부 holdout accuracy 0.9164, AI Hub/adversarial holdout 0.9229, Gemini verified holdout 0.8536, hard intent holdout 0.9747, region clarify natural holdout 0.9800, 문맥 해석 locked test 최신 micro-F1 0.9803, independent validation 0.9741, specific-facility adversarial 0.9946, rotating blind v4 fresh rule-only 0.9091/hybrid LinearSVC 0.9012/hybrid LogisticRegression 0.8968, blind chat eval v2 15/15 |
| 운영/배포 | 20% | 임시 확인 | Cloudflare Quick Tunnel로 외부 임시 확인 가능, 정식 배포 아님 |

## 완료된 핵심 항목

- 한국관광공사 무장애 여행 정보 OpenAPI 호출 확인
- TourAPI 엔드포인트별 일일 1,000건 사용량 가드와 당일 산출물 기반 사용량 부트스트랩 추가
- cache/fallback miss 때 live TourAPI 후보 조회를 사용하는 경로 추가
- 저장된 후보가 5장 미만일 때 자동 live 호출 대신 `최신 정보 더 찾기` 후속 버튼으로 명시적 live 보강 흐름 추가
- 같은 지역 반복 요청을 줄이는 프로세스 메모리 캐시 추가
- mvp/fallback-1/fallback-2/fallback-3 분할 수집 완료
- fallback Markdown 샘플 품질 감사 스크립트와 리포트 절차 추가
- 2026-05-16 이어받기 수집 후 샘플 감사 결과 808개 중 808개 파싱 성공, 필수 필드 누락 0개, 중복 콘텐츠ID 0개 확인
- 2026-05-16 서귀포시 100건 보강 후 `data/raw/tourism_accessible` 기준 Markdown은 904개다. Chroma 재색인 결과 905개 문서/914개 청크를 확보했다.
- 2026-05-16 fallback-only/live-enabled 100문항 eval 실행 완료, 자동 채점 실패 0건 확인
- 2026-05-16 선호/부정 조건, 감각 접근성, 애매 지역을 포함한 30문항 챌린지 eval 추가 및 fallback-only 자동 채점 실패 0건 확인
- 2026-05-16 대화 흐름 50시나리오 챌린지 eval 추가 및 fallback-only 자동 채점 실패 0건 확인. 확장 과정에서 최초 9건 실패를 찾고 후속 표현 인식, `A 말고 B` 지역 전환을 보강했다.
- 2026-05-16 신규 문제 탐색용 확장 eval을 단발 274문항, 대화 97시나리오까지 늘려 총 551건으로 확대했다. fallback-only와 live-enabled 전체 실행 모두 자동 채점 실패 0건을 확인했다.
- 2026-05-16 서귀포시 부족 카드가 남제주군 통합 지명 테스트를 막아 TourAPI로 서귀포시 100건을 보강했다. 보강 후 서귀포시 실내 박물관/전시, 산책, 가족 편의 질문이 카드 근거를 반환한다.
- `/tourism/chat`이 같은 `session_id` 안에서 마지막 성공 응답의 지역/조건/선호를 기억해 `더 보기`, `그중 시장 말고`, `유모차 말고 휠체어`, `중구로 좁혀줘` 같은 후속 질문을 처리
- 프로젝트 내부 평가셋, seed 발화, 재현 가능한 생성 발화, AI Hub 고신뢰 추출 발화로 16,254 rows 의도 분류 학습셋을 만들고, rule override + 문자 n-gram Naive Bayes shadow classifier를 `/tourism/chat` 대화 맥락 판단에 연결
- 2026-05-16 문맥 해석 라벨 체계를 intent와 분리했다. 라벨은 `strict_and`, `soft_and`, `or_condition`, `add_condition`, `replace_condition`, `exclude_condition`, `family_context`, `mobility_context`, `specific_facility_required` 9개다. 이 라벨은 모든 자연어 문맥을 덮는 완성형 분류가 아니라 추천 로직의 행동을 바꾸는 위험한 판단 축이다.
- 2026-05-17 문맥 해석 전용 학습셋을 4,400건, hard holdout을 4,800건으로 확장했다. `유모차`의 이동/가족 맥락 분리, 시설명 단독 문장, OR/strict 경계, `주차 말고 주제가 독특한 곳`, `추측하지 말고`, `A는 그만하고 B` 같은 문맥 반례를 추가했다.
- 2026-05-17 교체 문장 라벨을 보정했다. `수어 안내는 그만하고 오디오가이드 있는 후보만` 같은 문장은 버린 조건이 아니라 새 조건 쪽의 `replace_condition` + `specific_facility_required`로 본다. `추측하지 말고`의 `말고`는 교체/제외 마커로 보지 않도록 수정했다.
- 2026-05-17 문맥 해석 모델 비교 결과 locked test 4,800건 기준 `soft_and`를 참고/선택/완화 의도가 명시된 경우로 좁힌 뒤 최초 hybrid LogisticRegression은 exact 0.9187/micro-F1 0.9688이었다. 이후 `아니면 제외` strict 처리, 가족/이동/soft 라벨 보정, `휠체어 위주`, `조용한 곳` 같은 선택 조건 경계를 보강했고, 최신 locked test는 exact 0.9706/micro-F1 0.9860이다. independent validation 1.0000 또는 고득점은 품질 점수가 아니라 현재 작성된 경계 회귀셋 통과 결과로만 본다.
- 2026-05-17 위 LinearSVC/LogisticRegression 비교는 같은 hard holdout에서 본 baseline 탐색 결과로 격하했다. 별도 hard validation split이 없으므로 최종 채택 실험이 아니며, Codex/LLM hard-style 학습셋과 hard validation을 만든 뒤 같은 조건으로 다시 비교해야 한다.
- 2026-05-17 문맥 해석 실패 bucket은 fixed blind와 rotating blind에서 다시 드러났다. fresh rotating blind 80건은 최초 hybrid LinearSVC exact 0.5750/micro-F1 0.8163이었고, 같은 파일을 보고 경계 룰을 보강한 뒤 exact 0.9750/micro-F1 0.9919까지 올랐다. 보강 후 수치는 tuned diagnostic이므로 다음 판단은 새 rotating blind에서 한다.
- 2026-05-17 Hugging Face에서 확인한 `klue/roberta-base`, `klue/roberta-small`, `bespin-global/klue-roberta-small-3i4k-intent-classification`은 기본 경로가 아니라 파일럿 fine-tuning 후보로 둔다. 평가 스크립트의 2차 suitability score는 0.4429, recommendation은 `pilot_finetune`이다.
- 2026-05-17 KoBERT/KLUE-RoBERTa 파일럿 fine-tuning용 split을 strict family split으로 갱신했다. `data/processed/context_finetune/` 기준 최신 train 6,886건, validation 1,200건, test 4,800건이며, 각 row는 multi-label `label_vector`와 `template_family`를 포함한다.
- 2026-05-17 PyTorch/Transformers 의존성을 `requirements-ml.txt`로 분리하고 `klue/roberta-small` fine-tuning grid를 실행했다. 초기 grid는 validation 0.9993-1.0000이 반복돼 검증셋 실패로 판정했다. strict family split 재실험에서는 validation exact 0.8417/micro-F1 0.9241, locked test 단독 micro-F1 0.8594, rule hybrid locked test micro-F1 0.9474였다. 당시 기준선 hybrid LogisticRegression 0.9688을 넘지 못하고 평균 예측 시간도 0.8859ms로 더 느려 런타임 교체는 보류한다.
- 2026-05-17 ML 평가 운영 기준을 `docs/tourism/ml_evaluation_governance.md`로 분리했다. validation 1.0000, focused holdout 1.0000, 단일 accuracy 상승을 채택 근거로 쓰지 않고, overfit/underfit/leakage/outlier/latency/special error를 함께 본다. `scripts/audit_tourism_ml_experiment.py`는 transformer 파일럿 결과를 읽어 validation-hard gap과 기준선 미달을 자동으로 경고한다.
- 2026-05-17 Codex/LLM으로 hard-style 문맥 학습셋을 만들 수 있도록 `scripts/build_tourism_context_llm_generation_prompt.py`, `scripts/validate_tourism_context_llm_dataset.py`, `docs/tourism/context_llm_dataset_generation.md`를 추가했다. LLM 생성 결과는 schema/라벨/중복/기존 train·holdout overlap 검수를 통과해야 하고, `prepare_tourism_context_finetune_data.py --extra-train-input`으로만 병합한다.
- 2026-05-18 핵심어/동의어/오타 후보 5,000건을 생성/검증하고 리포트 기반 보강을 수행했다. promote candidate mismatch는 1,645 -> 726 -> 159로 줄었다. `장애인` 단독을 휠체어 조건으로 보던 과해석을 제거했고, `휠쳐`, `보조갼`, `앨리베이터`, `무단차`, `영상에 글자 안내` 같은 명확 후보를 정규화/조건 키워드에 반영했다. `리프트` 단독은 차량/예약 의미와 충돌하므로 보류하지만, `휠체어 리프트`, `장애인 리프트`, `승강 리프트`, `계단 리프트`, `지하철 리프트`, `시설/건물/관광시설 리프트`는 접근성 승강 설비로 반영했다. 공공기관으로만 한정하지 않는다. 후속 지침은 `docs/tourism/tourism_keyword_variant_followup.md`에 고정한다.
- 2026-05-17 SuperGemma4 문맥 라벨링 초기 실험을 실행했다. 이전 hard holdout 1,320건에서 `hybrid LogisticRegression` 오답 221건에만 호출했을 때 full exact는 0.8326에서 0.8879로 올랐지만, full micro-F1은 0.9179에서 0.9105로 내려갔다. latency는 mean 2191.1ms, p50 2159.8ms, p95 3028.6ms다. 현 프롬프트 방식은 런타임 보조 판단자로 채택하지 않고, QA/재라벨링 보조로만 둔다. 4,800건 holdout 기준 selective 실험은 아직 다시 돌리지 않았다.
- 2026-05-17 validation 1.0000 문제를 해결하기 위해 생성 family 단위 독립 validation 1,200건을 추가했다. 최신 split은 train 6,886건, validation 1,200건, locked test 4,800건이며 `--strict-family-split`으로 train/validation family overlap과 text overlap을 금지한다. 한 차례 independent validation exact 0.9000/micro-F1 0.9615까지 떨어지며 실패 bucket을 드러냈고, 그 오류를 보강한 뒤 현재는 다시 1.0000이다. 이 상태는 “완성”이 아니라 “현재 validation이 더 이상 약점을 못 드러냄”으로 본다.
- 2026-05-17 독립 validation 실패 bucket을 기반으로 `빼되`, `위주 결과는 뒤로`, `느낌만 아니면`, `따로따로 말고 한 장소`, `가능성 말고 문구`, `조건을 말한 건 아니고`, `근거 없으면 제외`, `필수 아님`, `확인된 카드만`, `참고만`, `둘 다 말하긴 했지만` 같은 경계 표현을 보강했다. 추가로 `아니면 제외/근거 없으면 빼줘`는 exclude가 아니라 strict 필수 조건으로 분리했고, 가족 동반 문장의 선택 시설은 `family_context + soft_and`로 라벨을 맞췄다.
- 2026-05-17 locked test의 `specific_facility_required` precision/recall/F1 1.0000을 의심하고 시설 조건 adversarial holdout 980건을 추가했다. 최초 exact 0.7102/micro-F1 0.8809에서 경계 보강 후 최신 exact 0.9929/micro-F1 0.9950이다. 이 focused 결과는 품질 점수가 아니라 현재 작성한 시설 조건 반례 통과 결과로만 본다.
- 2026-05-17 사람이 직접 쓴 holdout을 당장 확보할 수 없으므로 Codex LLM blind holdout을 별도 작성했다. `data/eval/tourism_context_blind_holdout.jsonl` 80건은 기존 generator family를 재사용하지 않는다. 최초 평가에서 rule-only exact 0.4750/micro-F1 0.7304, LogisticRegression 단독 exact 0.5125/micro-F1 0.7512, hybrid LogisticRegression exact 0.4500/micro-F1 0.7296으로 1.0000 착시가 깨졌다. 오류 bucket 보강 후 fixed blind는 hybrid LinearSVC exact 0.6250/micro-F1 0.8340까지 올랐지만, 같은 파일을 보강에 사용했으므로 최종 품질 점수로 쓰지 않는다.
- 2026-05-17 `scripts/generate_tourism_context_rotating_blind_holdout.py`로 fresh rotating blind 80건을 추가했다. 최초 hybrid LinearSVC exact 0.5750/micro-F1 0.8163으로 고정 blind 보강 뒤에도 새 문장에서는 일반화 약점이 남는다는 신호가 나왔다. 이후 같은 파일의 실패를 룰로 보강해 exact 0.9750/micro-F1 0.9919가 됐지만, 이는 해당 파일 대응 결과로만 본다.
- 2026-05-17 v1 rotating blind 보강 뒤 v2 rotating blind 80건을 추가했다. 최초 hybrid LogisticRegression exact 0.6000/micro-F1 0.8245로 다시 약점이 드러났고, `시설명은 상호/작품명일 뿐`, `보조견 테마 전시 말고 동반 가능 표기`, `보다는/후보가 많을 때만`, strict AND와 제외 표현 충돌을 보강했다. 보강 후 hybrid LinearSVC exact 0.9250/micro-F1 0.9719, locked test exact 0.9548/micro-F1 0.9803, independent validation exact 0.9242/micro-F1 0.9741, specific-facility adversarial exact 0.9918/micro-F1 0.9946이다. v2도 오류 분석에 사용했으므로 다음 품질 판단은 v3 rotating blind로 한다.
- 2026-05-17 v2 rotating blind 보강 뒤 v3 rotating blind 80건을 추가했다. 최초 hybrid LinearSVC exact 0.6625/micro-F1 0.8560으로 `보조 조건`, `필수로 보진 말자`, `유모차 대여`, `한 장소에 같이 없으면`, 시설명/작품명/별명 near-miss 약점이 다시 드러났다. 평가셋 라벨 중 `촉지도나 점자 안내`는 OR, `카페 말고`, `공연장은 빼고`는 exclude로 고쳐 라벨 정의 오류를 먼저 바로잡았다. 이후 경계 룰 보강으로 hybrid LinearSVC exact 0.9875/micro-F1 0.9960, rule-only 1.0000이 됐다. v3도 오류 분석에 사용했으므로 다음 품질 판단은 v4 rotating blind로 한다.
- 2026-05-17 문맥 약점이 실제 카드 반환에 미치는지 보기 위해 `data/eval/tourism_context_blind_chat_eval.jsonl` 10건을 추가했다. 최초 fallback-only direct 실행은 9/10 통과했고, `전주에서 시장 골목 말고 조용한 곳만 보고 싶어`가 `card_count_low`로 실패했다. 시장 제외 파싱, `취소` 표현, 선호 조건 hard filter를 보정한 뒤 최신 실행은 10/10 통과한다.
- 2026-05-17 v3 보강 뒤 v4 rotating blind 80건을 추가했다. fresh v4 결과는 rule-only exact 0.7375/micro-F1 0.9091, hybrid LinearSVC exact 0.7250/micro-F1 0.9012, hybrid LogisticRegression exact 0.7125/micro-F1 0.8968이다. 하이브리드 로지스틱 회귀는 계속 비교하지만 v4 최고는 아니며, 이 결과는 런타임 교체가 아니라 남은 boundary bucket을 실제 chat 영향 기준으로 선별해야 한다는 신호다.
- 2026-05-17 실제 `/tourism/chat` 카드 적합성 확장셋 `data/eval/tourism_context_blind_chat_eval_v2.jsonl` 15건을 추가했다. strict 시설, OR 감각 접근성, 제외 선호, 지역 교체, 미지원 주제, 저커버리지 무환각 케이스를 포함하고 fallback-only direct 실행에서 15/15 통과했다.
- 2026-05-17 독립 validation 기준으로 `klue/roberta-small`을 다시 학습했다. validation exact 0.8417/micro-F1 0.9241, locked test 단독 exact 0.7165/micro-F1 0.8594, rule hybrid locked test exact 0.8969/micro-F1 0.9474다. 당시 기준선 hybrid LogisticRegression locked test exact 0.9187/micro-F1 0.9688을 넘지 못하고 latency도 느려 `audit_tourism_ml_experiment.py` 판정은 `do_not_adopt_runtime`이다.
- 2026-05-16 의도 분류 ablation 검증 완료. rule-only 0.5605, project seed/generated 0.7854, project+AI Hub 0.8745, project+AI Hub+HF external 0.8632로 측정되어 AI Hub는 기본 학습에 유지하고 HF external은 재라벨링 전까지 실험용으로만 둔다.
- 2026-05-16 latency 측정 완료. classifier 로드는 약 19ms, 예측 p95는 0.0055ms로 답변 시간 영향은 사실상 없고, direct fallback chat p95는 95.6137ms였다.
- 2026-05-16 Gemini로 AI-generated independent holdout 770건을 만들고 2차 라벨 검수 후 676건을 확보했다. 일반화 가능한 rule override 보강 후 classifier baseline은 0.5488에서 현재 0.8536까지 올랐다.
- 2026-05-16 `show_more`, `live_topup`, `unsupported_request`, 애매 지역 경계 케이스 중심 hard intent holdout 990건을 추가했다. 2차 보강 전 0.8566에서 현재 0.9747로 올랐고, 같은 시점 AI Hub/adversarial holdout은 0.9229이다.
- 2026-05-16 Gemini verified holdout의 `clarify_region`이 35건뿐인 한계를 보완하기 위해 region clarify holdout을 추가했다. rule-boundary stress 960건은 1.0000이지만 contract/regression 테스트로 분리하고, 자연형 holdout 600건은 전체 0.9800이다. 자연형 holdout의 `clarify_region` 부분 집합 300/300 통과도 단독 품질 지표로 쓰지 않고 전체 natural 지표와 같이 본다. 1.0000이 반복되는 부분 셋은 "완성된 판단셋"이 아니라 반례가 아직 부족한 경계 테스트로 취급한다.
- 2026-05-16 `change_region`/`replace_condition` 후속 질문 경계 확인용 focused intent holdout 600건을 추가했다. 현재 1.0000이지만 생성형 집중 회귀셋이므로 품질 점수에서 제외한다. 이 셋은 실사용 품질을 증명하는 자료가 아니라, 새 반례를 추가해 계속 깨뜨려야 하는 최소 경계 방어선이다.
- 2026-05-16 실제 `/tourism/chat` 응답을 채점하는 `change/replace` 멀티턴 판단셋을 201건으로 확장했다. 지역 전환, 조건 교체, 단순 제외, 더 보기 유지, 맥락 없는 조건 요청, 간접 접근성 표현, 광역/시군구 전환을 카드/답변 기준으로 검사하며 fallback-only direct 실행에서 201/201 통과했다.
- 2026-05-16 별도 adversarial chat holdout 42건을 추가했다. 조사형 제외 표현, 과거 지명 뒤 지역 전환, 한 문장 안의 이중 `말고`, 맥락 없는 후속 발화, 중복 지명 clarification을 검사하며 fallback-only direct 실행에서 42/42 통과했다.
- 2026-05-16 멀티턴 판단셋 확장 중 `서귀포시 말고 제주시`가 이전 지역을 잡는 문제, `시장 말고 실내 박물관`의 새 선호를 제외로 오인하는 문제, `replace_condition`에서 이전 선호가 계속 누적되는 문제, 과거 지명이 `말고` 앞에 있을 때 계속 우선되는 문제, 광역 지역으로 바꿀 때 이전 시군구 코드가 새 지역에 섞이는 문제, `숙박은 빼고`처럼 조사가 붙은 제외 표현을 놓치는 문제를 찾아 수정했다.
- 2026-05-16 `더 보기`에서 후보 리스트가 전체 fallback으로 풀리는 문제를 20장 상한이 아니라 주소 기준 지역 필터 유지로 수정했다. 따라서 확인된 같은 지역 후보가 20장을 넘어도 임의로 자르지 않는다. 이후 20장 이상 반환 케이스 4개, 총 186장을 전수 검사해 지역 오류 0건, 요청 조건 근거 누락 0건을 확인했다.
- 2026-05-16 복합 조건 필터를 보강했다. 사용자가 `둘 다`, `모두`, `동시에`, `반드시`처럼 명시한 경우만 strict AND로 보고, 그 외 복합 조건은 전체 충족 후보를 우선하되 없으면 부분 근거 후보를 반환한다. 단 `점자블록`, `보조견`, `수어/자막`, `장애인 주차`, `장애인 화장실`, `기저귀 교환대`처럼 사용자가 직접 말한 세부 시설은 필수 근거로 유지한다.
- 2026-05-16 유모차 조건은 두 층으로 분리했다. `유모차/수유실/유아용 의자/영유아 가족 편의` 같은 직접 가족 편의 근거를 우선하고, 직접 근거가 없을 때만 `턱 없음/경사로/출입통로/엘리베이터/평탄` 같은 이동 가능성 근거를 보조로 본다. `아이랑`, `가족`, `영유아` 표현은 가족 편의 직접 근거를 요구한다.
- 2026-05-16 `수어 안내나 자막 안내`처럼 OR로 말한 감각 접근성 조건을 하나의 OR 근거 그룹으로 처리하고, `시장 말고` 같은 제외 후속 질문에서는 이전 필수 시장 근거가 세션에 남지 않도록 수정했다. 음식점/카페 제외는 `의자식 테이블`, `테이블 간격`, 음식점성 제목 단서까지 함께 본다.
- 2026-05-16 fallback-only direct chat eval 7개 파일 총 794건을 재실행해 전부 통과했다. 세부 결과는 `tourism_100_questions` 100/100, `tourism_challenge_questions` 30/30, `tourism_conversation_challenge` 50/50, `tourism_expanded_questions` 274/274, `tourism_expanded_conversation_challenge` 97/97, `tourism_change_replace_chat_holdout` 201/201, `tourism_adversarial_chat_holdout` 42/42다. 확인 후 TourAPI 사용량은 `areaBasedList2=144`, `detailCommon2=530`, `detailWithTour2=523`이다.
- Gemini API holdout은 현재 676건까지만 고정 평가 자산으로 두고, 추가 AI-generated independent holdout이 필요하면 Codex `gpt-5.4-mini` 또는 `gpt-5.3-codex-spark` 계열로 새 파일을 만든다.
- 이벤트 로그에 `preferences`, `excluded_preferences`, `ml_intent`, `ml_intent_confidence`를 추가해 개발 모드에서 규칙/학습 신호 차이를 확인 가능
- 2026-05-15 로컬 모델 추론 보조 벤치마크 실행 완료, `gemma4:e4b`와 `huihui_ai/gemma-4-abliterated:e4b`는 native thinking이 되지만 30초 이상 지연 확인
- 2026-05-27 Apple Silicon 전용 provider 전환 검토를 종료했다. 당시 서비스 모델과 실제 관광 corpus 기준에서는 Ollama `SuperGemma4` generation과 `bge-m3` embedding을 유지했다. 전환 실험용 venv, 모델 cache, 산출물, 전용 비교 스크립트는 디스크 절약을 위해 삭제했다. AutoRAG는 별도 venv의 retrieval-only 실험 도구로 되살렸지만 운영 검색은 기존 Chroma vector-only 구조를 유지한다.
- 2026-06-07 기본 답변 모델을 `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL`로 변경했다. 같은 관광 재랭킹/답변 프롬프트 기준 첫 호출 제외 평균은 Unsloth Gemma4가 재랭킹 655ms, 답변 2359ms로 SuperGemma4보다 빨랐고, 답변도 더 상담형이었다. 두 태그 모두 Ollama native `think=true`는 지원하지 않는다.
- 2026-05-27 한국어 BM25 토크나이저 재실험을 추가했다. corpus 1,010개, QA 192개에서 `bge-m3` vector-only top40 recall 0.6276/MRR 0.4052가 `ko_kkma` BM25 top40 recall 0.5072/MRR 0.2937, `ko_okt` BM25 top40 recall 0.3971/MRR 0.3332보다 높았다. `space`는 한국어 BM25에 부적합하고, `ko_okt`는 BM25 후보 중 상위 카드 안정성이 좋아 오프라인 비교 후보로 둔다. 운영은 Chroma vector-only `top_k=40` 유지다.
- 2026-05-27 통합 벤치마크를 재실행했다. 중형 120문항은 `current_runtime` 104/120, 노이즈 현실형 200문항은 `roberta_small_candidate` 174/200, `et5_roberta_combined` 172/200, `current_runtime` 168/200이다. medium/noisy 세트에서는 reasoning assist가 실제 0회라 LLM 품질 비교로 보지 않고, 20문항 LLM 트리거 eval에서 SuperGemma4/Gemma3/Gemma4/OFF 모두 20/20 통과했다. 2026-06-07 이후 기본값은 reasoning assist OFF, 필요 시 현재 기본 Unsloth Gemma4 `think=false` 제한 실험이다.
- `data/raw/tourism_accessible` 기준 904개 Markdown fallback 확보
- MVP fallback 수집은 지역별 최소 안전망 기준으로 90% 완료다. 남은 10%는 20문항 eval에서 드러나는 부족 지역만 보강하는 작업이다.
- 전국 시군구 fallback은 TourAPI 지역 코드 234개 중 228개 시군구가 3장 이상 확보됐다. 청원군, 마산시, 진해시, 남제주군, 북제주군은 부족 지역으로 표시하지 않고 현재 행정구역 기준 안내 예외로만 관리한다. 공식 무장애 상세 3장 미만 지역은 계룡시 1장이다. 2026-05-17 재수집에서도 무장애 전용 목록은 1건만 반환했고, 일반 관광 검색 8건 중 나머지 7건은 무장애 상세가 없어 접근성 카드로 편입하지 않았다. 행안부 현행 시군구 매칭은 228개이며, 250개는 확정 행정구역 수가 아니라 행정시/일반구/생활권 표현까지 포함할 수 있는 제품 목표 상한으로만 둔다.
- 행안부 주민등록주소코드 기반 행정동/법정동 매칭 데이터 생성
- 지역 코드 캐시 생성 및 누락/손상 진단
- `/tourism/chat` endpoint 추가
- 관광 카드 Markdown codec 공유화
- Retriever 실패 시 local sample fallback과 `degraded/warnings` 노출
- 시군구 자동 확장 금지 정책 반영
- `근처/주변/가까운/인근`은 시군구 안의 가까운 후보 선호로 처리하고, 명시적 `전체로 넓혀줘`류 요청에서만 상위 지역 확장
- `중구` 같은 동명이 시군구는 지역 선택 후보 반환
- 관계 호칭만으로 나이 추정하지 않음
- `베리어프리`, `유아차`, `기저귀`, `어린이` 등 사용자 표현 동의어를 관광 조건으로 인식
- 카드 랭킹에서 질문 조건과 직접 맞는 raw 편의정보 키와 가족 편의 근거를 우선 반영
- 카드 위 답변에 태그뿐 아니라 실제 편의정보 근거 일부를 함께 노출
- `tests/test_tourism_quality_regression.py`에 지역 해석 110개, 조건 인식 29개, 랭킹/근거 문장 회귀 케이스 추가
- 복합 질문에서만 LLM 추론 보조를 호출해 후보 카드 재랭킹과 확인 필요 메모를 반환
- 정적 웹 UI `/tourism-ui/` 추가
- `/tourism-ui/`를 대시보드형 화면에서 메신저형 관광 상담 UI로 개편
- `/tourism-ui/` 개발 모드와 릴리즈형 사용자 화면을 분리. 기본 개발 모드는 `DBG` 패널에 API 주소, Swagger/ReDoc/OpenAPI, 응답 경로 진단을 보이고, `?mode=release`/`?debug=0`은 내부 진단 없이 앱형 상담 화면만 보인다.
- 사용자 질문 말풍선, bot typing indicator, 입력/오류/카드 반환 toast, 카드 등장 애니메이션, 모바일 1열 카드 레이아웃, release 빈 상담 시작 상태를 추가
- `/tourism-ui/`가 브라우저 세션별 `session_id`를 `/tourism/chat`에 보내도록 수정했다. `비우기`를 누르면 새 세션으로 초기화한다.
- 2026-05-17 UI 중간 QA를 live TourAPI 사용 가능 모드에서 실행했다. Playwright Chromium으로 개발 모드 20회, 릴리즈 모드 20회 대화형 입력을 수행했고, Computer Use로 Chrome 개발/릴리즈 화면을 눈으로 확인했다. 결과는 38/40 통과, 개발 18/20, 릴리즈 20/20이다. `live_top_up` 4회가 관측되어 fallback-only가 아님을 확인했다. 실패는 `수어 안내나 자막 안내` 후속 질문이 `unknown` 0장으로 끝난 건과 `오늘 환율 알려줘` 비관광 질문이 관광 카드로 응답한 건이다. 추적 가능한 요약은 `docs/project/tourism_ui_midcheck_20260517.md`에 있고, 원본 JSON/스크린샷은 `data/generated/tour_api/ui_qa/`에 있다.
- 추천 카드 위 긴 답변을 기본 접힘 처리하고 `전체 보기`/`접기`를 추가
- 추천 카드에 `상세 정보` 펼침과 장소명/주소 기반 `지도 검색`을 추가
- 콘텐츠 ID만으로 만든 `access.visitkorea.or.kr/detail/...` 링크가 비정상 접근으로 떨어져 잘못된 원문 URL 생성을 중단
- `TourAPIService`에 raw SQLite response cache를 추가했다. 캐시 적중은 실제 공공데이터 호출이 아니므로 일일 사용량에 기록하지 않고, 저장 params/cache key에는 `serviceKey`를 넣지 않는다.
- Flutter 앱 repo `cheng80/chatbot_rag_app`는 최신 `/tourism/chat` 응답 계약, live update pending 상태, 안전하지 않은 VisitKorea 추정 링크 숨김, 단색 Material 지도 아이콘, 앱 전용 `.env.example` 정리를 반영했다.
- v4 문맥 mismatch 중 실제 카드 반환에 영향 있는 10건을 `data/eval/tourism_context_v4_chat_impact_eval.jsonl`로 승격했다.
- noisy realistic 잔여 28건은 `docs/tourism/noisy_realistic_residuals.md`에 희소 접근성 근거 부족 bucket으로 고정했다.
- `패스`를 제외 선호 marker로 처리해 `숙박업소처럼 보이는 후보는 패스` 같은 표현이 unsupported로 빠지지 않게 고정했다.
- Cloudflare Quick Tunnel 외부 확인 흐름 문서화
- Swagger/ReDoc/OpenAPI JSON 링크를 UI에 노출
- 발표용 캡처와 시연 시나리오를 `docs/project/demo_capture_scenarios.md`에 정리

## 남은 자동 작업 순서

아래 목록은 사람이 수동으로 표본 채점하거나 화면을 눈으로 확인해야 하는 일을 제외한 실행 순서다. 수동 판단이 필요한 `live 조회 표본 QA`, `확장 eval 수동 채점`, `의료 안전 정보 확장 판단`은 별도 보류 항목으로 둔다. Flutter는 전환 여부 결정 대상이 아니라 이미 존재하는 별도 앱 repo 동기화 대상으로 관리한다.

| 순서 | 우선순위 | 작업 | 완료 조건 | 현재 위치 |
|---:|---|---|---|---|
| 1 | P1 | v4 chat impact eval 유지 | `data/eval/tourism_context_v4_chat_impact_eval.jsonl`을 direct eval로 돌려 실제 카드 반환 영향이 회귀하지 않음 | `data/eval/tourism_context_v4_chat_impact_eval.jsonl` |
| 2 | P1 | noisy realistic 잔여 28건 데이터 보강 후보화 | 수어/자막, 점자/촉지도, 보조견, strict combo 부족을 데이터 수집 후보로 분리하고 코드 과수정 금지 | `docs/tourism/noisy_realistic_residuals.md` |
| 3 | P1 | LLM hard-style v4/blind targeted batch 생성 | 2026-05-27 1,000건 batch는 검수/병합 완료. 다음은 v4/blind failure bucket을 겨냥한 새 batch 필요 | `docs/tourism/context_llm_dataset_generation.md` |
| 4 | P2 | 지역명 alias 제품 target list 결정 | 228/234/250 차이를 기준으로 실제 사용자 입력 대상 목록을 별도 정책으로 고정 | `docs/tourism/admin_region_aliases.md` |
| 5 | P2 | 로컬 AI provider 비교 갱신 | Apple Silicon 전용 provider 전환 검토 종료. Ollama `Unsloth Gemma4` + `bge-m3` 유지. AutoRAG는 별도 venv retrieval-only 실험 도구로 재도입 | `docs/tourism/tourism_model_reasoning_benchmark.md` |
| 6 | P3 | event log SQLite 전환 판단 | JSONL 조회/대시보드 필요가 생기면 SQLite schema로 이동, 아니면 보류 | `TODOS.md`, `TourismQueryEventLogger` |
| 7 | P3 | 초급자용 재현 문서 초안 작성 | 사용자 요청에 따라 보류. 재개 시 설치, 색인, 테스트, 서버, 터널, UI 확인을 순서대로 작성 | `docs/README.md` |

## 다음 자동 체크포인트

1. 백엔드 회귀 테스트를 확인한다.

```bash
.venv/bin/python -m pytest tests/test_tourism_query_service.py tests/test_tourism_chat_service.py tests/test_eval_tourism_chat_script.py -q
node --check frontend/web/app.js
git diff --check
```

2. noisy realistic 잔여 실패를 재확인한다.

```bash
TOURISM_LIVE_LOOKUP_ENABLED=false .venv/bin/python scripts/eval_tourism_chat.py --direct --input data/eval/tourism_noisy_realistic_chat_eval_v1_200.jsonl --output data/generated/tour_api/eval_runs/noisy_realistic_v1_200_topk40_service_scope_copy_fix.jsonl
```

3. v4 chat impact 회귀셋을 확인한다.

```bash
TOURISM_LIVE_LOOKUP_ENABLED=false .venv/bin/python scripts/eval_tourism_chat.py --direct --input data/eval/tourism_context_v4_chat_impact_eval.jsonl --output data/generated/tour_api/eval_runs/tourism_context_v4_chat_impact_latest.jsonl
```

4. fallback 샘플 감사와 시군구 예외 리포트를 갱신한다.

```bash
.venv/bin/python scripts/audit_tourism_samples.py
```

4. 의도 분류 변경 뒤에는 발화셋, 학습셋, 모델, 지표를 순서대로 갱신한다.

```bash
.venv/bin/python scripts/generate_tourism_intent_utterances.py
.venv/bin/python scripts/extract_aihub_tourism_intent_utterances.py
.venv/bin/python scripts/build_tourism_intent_training_set.py
.venv/bin/python scripts/train_tourism_intent_classifier.py
.venv/bin/python scripts/benchmark_tourism_intent_ablation.py
.venv/bin/python scripts/benchmark_tourism_latency.py
```

5. 문맥 해석 변경 뒤에는 rule/NB/Linear 비교와 suitability를 갱신한다.

```bash
.venv/bin/python scripts/generate_tourism_context_interpretation_data.py
.venv/bin/python scripts/train_tourism_context_classifier.py
.venv/bin/python scripts/eval_tourism_context_classifier.py
```

6. ML/Transformer 실험은 감사 스크립트로 채택 가능성을 먼저 확인한다.

```bash
.venv/bin/python scripts/audit_tourism_ml_experiment.py --transformer-metrics data/generated/tour_api/context_transformer_independent_validation/metrics.json --context-baseline-metrics data/generated/tour_api/context_classifier_eval_independent_test_latest.json
```

7. Codex/LLM hard-style 학습셋은 prompt 생성, JSONL 후보 확보, schema/overlap 검수, extra train 병합 순서로만 진행한다. prompt 생성은 완료됐고, 다음은 candidate JSONL 확보 뒤 검수다. 준비사항은 `docs/tourism/context_llm_dataset_generation.md`의 `1-1. 다음 실행 전 준비사항`에 고정했다.

```bash
.venv/bin/python scripts/validate_tourism_context_llm_dataset.py --input data/processed/tourism_context_hard_style_extra_train.candidate.jsonl
```

8. change/replace와 adversarial chat 회귀셋을 재생성·재평가한다.

```bash
.venv/bin/python scripts/generate_tourism_change_replace_chat_holdout.py
TOURISM_LIVE_LOOKUP_ENABLED=false .venv/bin/python scripts/eval_tourism_chat.py --direct --input data/eval/tourism_change_replace_chat_holdout.jsonl --output data/generated/tour_api/eval_runs/tourism_change_replace_chat_holdout_latest.jsonl
.venv/bin/python scripts/generate_tourism_adversarial_chat_holdout.py
TOURISM_LIVE_LOOKUP_ENABLED=false .venv/bin/python scripts/eval_tourism_chat.py --direct --input data/eval/tourism_adversarial_chat_holdout.jsonl --output data/generated/tour_api/eval_runs/tourism_adversarial_chat_holdout_latest.jsonl
```

9. Flutter 앱 repo를 최신 백엔드 계약과 동기화한다.

```bash
cd ../chatbot_rag_app
flutter test
dart format --set-exit-if-changed lib test
```

10. 최신 실행 결과를 `README.md`, `docs/project/next_session_prompt.md`, `docs/project/demo_capture_scenarios.md`, `../chatbot_rag_app/README.md`에 반영한다.

## 2026-05-26 자동 실행 결과

- 현재 미커밋 live update 변경 검증: `tests/test_tourism_chat_service.py` 70 passed, `node --check frontend/web/app.js` 통과, `git diff --check` 통과.
- TOP_K=40 확인: `app/core/config.py`의 `TOP_K` 기본값은 40이고 `Retriever.retrieve()`가 `settings.top_k`를 vector search `top_k`로 전달한다. 코드 수정 없이 반영 상태로 확인했다.
- TOP_K=40 direct eval:
  - `data/generated/tour_api/eval_runs/tourism_challenge_questions_topk40.jsonl`: 30 rows, failures 0
  - `data/generated/tour_api/eval_runs/residual_hard_chat_topk40.jsonl`: 80 rows, failures 0
  - `data/generated/tour_api/eval_runs/noisy_realistic_v1_200_topk40.jsonl`: 200 rows, failures 42
  - `data/generated/tour_api/eval_runs/noisy_realistic_v1_200_topk40_gated_roberta.jsonl`: 200 rows, failures 42
- unsupported 답변 문구를 서비스 범위 중심으로 수정한 뒤 `data/generated/tour_api/eval_runs/noisy_realistic_v1_200_topk40_service_scope_copy_fix.jsonl`은 200 rows, failures 28이다. `answer_missing_any_term` 14건은 사라졌고, 남은 실패는 `card_count_low` 21, `card_missing_required_terms` 21, 멀티턴 card 근거 부족, `answer_missing_term` 1건이다. 즉 unsupported copy 문제는 해결됐고, 남은 noisy 실패는 주로 수어/자막, 점자블록/촉지도, 보조견 같은 희소 접근성 카드 부족이다.
- 전체 회귀: `.venv/bin/python -m pytest -q`는 362 passed, 2 warnings. 이후 `node --check frontend/web/app.js`와 `git diff --check`도 통과했다.
- fallback 샘플 감사: `scripts/audit_tourism_samples.py` 결과 files=904, parsed=904, parse_failures=0, duplicates=0, missing_required=0. 리포트는 `data/generated/tour_api/tourism_sample_audit.md`에 갱신됐다.
- 시군구 예외 리포트: `data/generated/tour_api/sigungu_fallback_exception_report.md`와 `.json` 생성. TourAPI 시군구 234개, 행안부 현행 매칭 228개, 과거 지명 예외 5개, 공식 무장애 상세 저커버리지 1개로 고정했다.
- 문맥 v4 영향 자동 선별: `data/generated/tour_api/context_v4_chat_impact_report.json` 생성. v4 rule mismatch 20건 중 `card_filter_or_session_behavior` 10건, `ranking_or_copy_context` 10건으로 분류했다. `data/generated/tour_api/context_classifier_eval_v4_latest.json` 기준 best는 `hybrid_linear_svc`, exact 0.7375, micro-F1 0.9048이다.
- keyword variant review queue 자동 분류: `keyword_variant_20260518_5000_after_bucket_patch_review_queue.jsonl` 159건을 `data/generated/tour_api/keyword_variant_reports/keyword_variant_20260518_5000_auto_classified_review_queue.json`과 `.jsonl`로 분류했다. 자동 bucket은 `defer_paraphrase` 63건, `unsupported_collision` 96건이다. 즉시 promote할 안전한 typo/spacing 후보는 이 queue에서는 따로 나오지 않았다.
- intent pipeline 재생성:
  - `tourism_intent_generated_utterances.jsonl`: 13,200 rows
  - `tourism_intent_aihub_utterances.jsonl`: 2,700 rows
  - `tourism_intent_training.jsonl`: 16,254 rows
  - `tourism_intent_classifier.json` 재학습 내부 split accuracy: 0.8737
- intent holdout 결과:
  - Gemini verified holdout: 0.8550
  - hard holdout: 0.9747
  - region clarify natural holdout: 0.9800
  - change/replace natural holdout: 1.0000
  - adversarial holdout: 0.9264
  - ablation 기본 모델(`project_plus_aihub`): 0.9229
- latency benchmark: direct fallback chat overall mean 212.6983ms, p95 283.4613ms. Retriever `top_k=40` vector search only mean 1.2751ms, p95 1.9912ms이고 embed+vector retrieve p95 86.7760ms다.
- ML 감사: `audit_tourism_ml_experiment.py` 결과 `do_not_adopt_runtime`. 주요 사유는 validation-hard gap, 기준선 대비 품질 개선 부족, latency regression이다. Transformer/LLM 보조는 런타임 채택하지 않는다.
- LLM hard-style 학습셋 prompt 생성: `data/generated/tour_api/context_llm_prompts/context_llm_generation_prompt_001.md` 생성 완료. candidate JSONL이 아직 없으므로 검수/병합은 다음 단계다.
- SuperGemma4 bounded selective 재평가: `data/generated/tour_api/supergemma_context_eval_latest.json` 갱신. 4,800 rows 중 hybrid mismatch 105건, 그중 50건만 평가했다. full exact는 0.9781 -> 0.9792로 소폭 상승했지만 selected exact는 0.1000, latency mean 2867.9ms/p95 3861.8ms라 런타임 보조로 채택하지 않고 QA/재라벨링 보조로 유지한다.
- 지역명 alias 회귀 테스트: 성남 분당구 -> 경기 성남시, bare 일반구 다중 매핑 -> clarification 테스트를 추가했다.
- Flutter 앱 repo 확인: `project root_app`는 `main...origin/main`이며 `cheng80/chatbot_rag_app` 원격을 사용한다. 이미 Flutter 전환본이 있으므로 남은 작업은 전환 여부 결정이 아니라 최신 백엔드 계약/문서/테스트 동기화다.

## 2026-05-27 자동 실행 결과

- 남은 작업 표를 최신 상태로 갱신했다. Flutter 앱 동기화, persistent TourAPI raw response cache, 시군구 fallback 예외 리포트 정기 갱신은 완료 항목으로 내리고 남은 자동 작업에서 제외했다.
- `data/eval/tourism_context_v4_chat_impact_eval.jsonl` 10건을 추가했다. `TOURISM_LIVE_LOOKUP_ENABLED=false .venv/bin/python scripts/eval_tourism_chat.py --direct --input data/eval/tourism_context_v4_chat_impact_eval.jsonl --output data/generated/tour_api/eval_runs/tourism_context_v4_chat_impact_latest.jsonl` 실행 결과 failures 0이다.
- v4 eval 작성 중 `숙박업소처럼 보이는 후보는 패스`가 unsupported로 흐르는 경계가 확인되어 `패스`를 제외 선호 marker로 추가했다.
- noisy realistic 잔여 28건은 `docs/tourism/noisy_realistic_residuals.md`에 sensory/tactile/service animal/strict combo/multiturn evidence low coverage bucket으로 고정했다. 코드 과수정 대신 데이터 보강 후보로 관리한다.
- 지역명 alias 회귀 테스트를 확장했다. 부모 도시가 명시된 일반구, 동명이 법정동/행정동 ambiguity, 부모 도시가 명시된 법정동 확정을 테스트로 고정했다.
- LLM hard-style 학습셋 5번 작업 준비사항은 `docs/tourism/context_llm_dataset_generation.md`에 정리했다. 필요한 것은 LLM JSONL 후보 파일, 최소 250 valid rows, schema/라벨/overlap 검수 통과, extra train 병합 전 reject 사유 확인이다.
- LLM hard-style 1,000건 기존 batch를 최신 validator로 검수했다. `data/processed/tourism_context_llm_hard_training_20260527.valid.jsonl`은 1,000/1,000 valid, rejected 0이다.
- extra train 병합 산출물은 `data/processed/context_finetune_20260527_llm_hard_1000/`이다. source train 5,400 rows, train 4,599, validation 801, test 4,800이다.
- 별도 NB model `data/generated/tour_api/context_classifier_llm_hard_20260527.json`을 학습했다. 내부 split exact 0.7087, micro-F1 0.8422다.
- 독립 평가 결과 hard holdout은 rule/hybrid와 동률 수준이지만, v4 rotating blind와 blind holdout에서는 개선이 없다. v4 rule-only 0.7500/0.9127, best hybrid 0.7500/0.9127. blind rule-only 0.7750/0.8934, best hybrid 0.7375/0.8826이다. 따라서 런타임 채택은 하지 않는다.

Flutter 앱 갱신은 별도 repo에서 진행한다.

## 빠른 확인 명령

장시간 실행 서버는 Codex 백그라운드 세션으로 조용히 띄우지 않는다. VS Code/Cursor 같은 에디터 내장 터미널의 새 터미널에서 실행해 사용자가 로그와 종료 상태를 직접 확인한다. 여기서 말하는 터미널은 외부 터미널 앱이 아니라 에디터 안에서 보이는 터미널이다.

FastAPI와 Cloudflare는 같은 명령이 아니다. 외부 확인이 필요하면 터미널을 2개 연다.

터미널 1: FastAPI 서버

오늘처럼 TourAPI 호출을 더 쓰지 않을 때는 fallback-only로 실행한다.

```bash
.venv/bin/python -m pytest -q
TOURISM_LIVE_LOOKUP_ENABLED=false .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

외부 확인 URL 형식:

```text
https://...trycloudflare.com/tourism-ui/
```

터미널 2: Cloudflare Quick Tunnel

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```
