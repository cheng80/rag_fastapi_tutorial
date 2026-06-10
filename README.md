# RAG FastAPI Tutorial Workspace

이 폴더는 기존 `chatbot_rag` 프로젝트를 복사하거나 재사용하지 않고, 초급 개발자가 빈 환경에서 RAG/FastAPI 웹 채팅 프로젝트를 순차적으로 만들 수 있도록 튜토리얼북과 검증 산출물을 준비하는 독립 작업 공간이다.

## 원칙

- 기존 프로젝트의 `app/`, `docs/`, `notebooks/`, `scripts/`, `frontend/`, `.venv`를 재사용하지 않는다.
- 튜토리얼 본문은 새 프로젝트를 처음부터 만든다는 전제로 작성한다.
- 기존 프로젝트는 설계 참고와 부록의 개념 매핑에만 사용한다.
- 노트북은 실제 실행 결과가 남는 검증 산출물로 관리한다.
- 외부 LLM 없이 로컬 모델, FastAPI, ChromaDB, Notebook, Markdown만으로 따라갈 수 있게 한다.

## 폴더 구조

```text
rag_fastapi_tutorial/
├─ PLAN.md                 # 전체 실행 계획
├─ docs/
│  ├─ chapters/            # 장별 Markdown 원고
│  └─ references/          # 용어, 체크리스트, 오류 해결표
├─ notebooks/
│  ├─ templates/           # 작성 전 노트북 템플릿
│  └─ executed/            # 실제 실행 검증 완료 노트북
├─ project_template/       # 튜토리얼을 따라 만들 최종 예제 프로젝트 골격
├─ evidence/               # 명령 출력, 테스트 로그, 노트북 실행 증거
└─ notion/                 # Notion 최종 정리용 Markdown/export 초안
```

## 다음 작업

1. `PLAN.md`의 단계와 산출물 범위를 확정한다.
2. `docs/chapters/00_roadmap.md`부터 장별 Markdown 초안을 작성한다.
3. 각 장에 대응하는 검증 노트북 템플릿을 만든다.
4. 새 Python 가상환경 기준으로 노트북을 실행하고 `notebooks/executed/`에 저장한다.
5. 검증이 끝난 Markdown을 Notion 페이지로 정리한다.
