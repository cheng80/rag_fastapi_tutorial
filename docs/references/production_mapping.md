# 원본 프로젝트 매핑

| 튜토리얼 산출물 | 원본 프로젝트 역할 |
| --- | --- |
| `project_template/app/main.py` | FastAPI 앱 생성, 라우터 등록, `/tourism-ui/` 연결 |
| `project_template/app/api/deps.py` | 서비스 의존성 조립 |
| `project_template/app/api/routes/tourism.py` | 관광 상담과 지역 목록 API |
| `project_template/app/services/rag_service.py` | 일반 RAG 답변 생성 |
| `project_template/app/services/tourism_chat_service.py` | 관광 상담 답변과 카드 생성 |
| `project_template/frontend/web/index.html` | 실제 사용자용 무장애 관광 상담 화면 |
| `project_template/data/processed/tour_area_codes.json` | 전국 광역/시군구 코드 |
| `tests/test_project_template_parity.py` | 튜토리얼 산출물의 원본형 표면 검증 |
| `tests/test_tutorial_docs.py` | 교재 구조와 검증 노트북 구조 검증 |

이 매핑은 코드 위치를 찾기 위한 참고다. 실제 튜토리얼 본문은 `docs/chapters/`에서 장별로 읽는다.
