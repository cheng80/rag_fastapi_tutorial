# 문서 인덱스

마지막 갱신: 2026-05-25

## 0. 폴더 구조

```text
docs/
├─ project/      01 프로젝트 목표, 진행도, 검토 브리프, 다음 세션 handoff
├─ rag/          02 일반 RAG 챗봇 설계
├─ tourism/      03 관광 챗봇 기획, TourAPI 응답 전략, 데이터 운영, eval
├─ design/       04 관광 챗봇 웹 UI 디자인 기준
└─ etc/          90 환경 정리, 도구 메모, 외부 원자료 같은 참조 문서

notebooks/
└─ 이벤트 로그 분석, 초기 API 탐색, 모델 비교 보조 노트북
```

## 1. 순서대로 읽을 문서

| 순서 | 문서 | 용도 |
|---:|---|---|
| 00 | `project/next_session_prompt.md` | 새 세션 시작 문서 |
| 01 | `project/professor_review_brief.md` | 외부 검토자에게 보여줄 단일 브리프 |
| 02 | `project/GOAL.md` | 현재 MVP 목표와 판정 기준 |
| 03 | `project/progress_overview.md` | 전체 진행도와 남은 작업 |
| 04 | `rag/rag_chatbot_design.md` | 일반 RAG 챗봇 구조 |
| 05 | `tourism/accessible_tourism_mvp_plan.md` | 관광 챗봇 구현 플랜 |
| 06 | `tourism/tourism_response_strategy_decision.md` | cache/RAG-first + live-on-miss 전략 결정 |
| 07 | `tourism/tourism_data_operations.md` | fallback 수집, 호출량, 시군구 규모, 샘플 QA 통합 문서 |
| 08 | `tourism/admin_region_aliases.md` | 행정동/법정동 지역명 매칭 데이터 |
| 09 | `tourism/tourism_eval_questions.md` | 100문항/30문항/50시나리오 평가셋 |
| 10 | `tourism/tourism_intent_classifier.md` | 후속 질문 의도 분류기와 학습셋 |
| 11 | `tourism/ml_evaluation_governance.md` | ML 평가 운영 기준, 과적합/과소적합/holdout 판정 |
| 12 | `tourism/context_llm_dataset_generation.md` | Codex/LLM hard-style 학습셋 생성 절차 |
| 13 | `tourism/tourism_keyword_variant_followup.md` | 핵심어/동의어/오타 보강 후속 작업과 보류 기준 |
| 14 | `tourism/tourism_model_reasoning_benchmark.md` | 로컬 LLM 추론 보조 비교 |
| 15 | `tourism/autorag_retrieval_experiment.md` | AutoRAG retrieval-only 오프라인 검색 실험 |
| 16 | `tourism/tourism_service_enhancement_ideas.md` | 기본 추천 기능 이후의 편의 기능 보강안 |
| 17 | `design/tourism_chatbot_DESIGN.md` | `/tourism-ui/` 디자인 기준 |
| 18 | `project/demo_capture_scenarios.md` | 발표용 캡처와 시연 질문 |
| 19 | `project/mvp_quality_work_log.md` | 작업 이력과 산출물 목록 |

## 2. ETC 참조 문서

프로젝트 흐름을 이해하는 데 필수는 아니지만 필요할 때 참고한다.

| 문서 | 용도 |
|---|---|
| `etc/setup/remove_anaconda_mac_guide.md` | 다른 Mac에서 conda/Anaconda 정리할 때 참고 |
| `etc/references/(공고문)『2026_생성형_AI_활용_관광_프롬프톤_부문』_공고문.pdf` | 공모전 원자료 |
| `etc/references/개방데이터_활용매뉴얼(국문)/` | 국문 관광정보 서비스 원자료 |
| `etc/references/개방데이터_활용매뉴얼(무장애여행)/` | 무장애 여행 정보 원자료 |
| `../notebooks/tourism_event_log_analysis.ipynb` | `/tourism/chat` JSONL 이벤트 로그 분석 |
