# 16. Notion

## 이번 장에서 만들 것
최종 Notion 튜토리얼북 초안과 검증 스크립트를 만든다. 초안은 진행 보고서가 아니라 1장부터 16장까지 순서대로 따라 하는 교재여야 한다.
## 왜 필요한가
마지막 산출물은 로컬 파일만이 아니라 Notion에서 읽을 수 있는 순서형 교재다. 데이터 추가, QA 증거, parity 현황은 별도 업데이트 글처럼 위에 쌓지 않고 필요한 장의 설명 안에 녹인다.
## 최종 폴더 상태
`notion/rag_fastapi_tutorial_notion_draft.md`, `scripts/validate_notion_tutorial_book.py`
## 새로 만들 파일
`notion/rag_fastapi_tutorial_notion_draft.md`
## 코드 전체
```bash
python3 scripts/validate_notion_tutorial_book.py
```
## 코드 흐름 설명
Notion draft는 학습자가 위에서 아래로 읽는 순서를 먼저 보여준다. 관광 markdown seed/cache는 9장 Cache/Fallback 학습 재료로 설명하고, 실제 API/UI 검증은 14장과 15장 흐름 안에서 확인한다.
## 실행 명령
```bash
python3 scripts/validate_notion_tutorial_book.py
```
## 성공 기준
Notion draft가 16장과 8개 Notebook 이름을 포함하고, 첫 화면이 최종 판정이나 업데이트 내역이 아니라 튜토리얼 시작 화면이다.
## 검증 노트북
executed Notebook 전체
## 자주 나는 오류와 해결
- 오류: Notion 맨 위에 최신 데이터 업데이트나 QA 증거만 붙인다.
- 해결: 해당 내용이 필요한 장 본문에 들어가게 다시 배치한다.

기존 Notion 페이지를 덮어쓰기 전에 로컬 draft와 validator를 먼저 통과시킨다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] Notion draft 확인
- [ ] validator 통과
- [ ] Notion 페이지 업데이트 확인
