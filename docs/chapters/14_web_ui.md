# 14. Web UI

## 이번 장에서 만들 것
무장애 관광 상담 웹 UI와 선택형 조건 입력을 만든다.
## 왜 필요한가
최종 사용자는 API가 아니라 웹 화면으로 상담한다.
## 최종 폴더 상태
`frontend/web/index.html`, `app.js`, `styles.css`, `option_flow_builder.js`
## 새로 만들 파일
`frontend/web/*`
## 코드 전체
```bash
cd project_template
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
## 코드 흐름 설명
웹 UI는 지역 목록을 가져오고 사용자의 질문을 `/tourism/chat`으로 보낸다.
## 실행 명령
```bash
python -m pytest tests/test_tourism_option_flow_ui.py -q
```
## 성공 기준
채팅형/선택형 입력, 카드, 출처, 도움말, 진단 패널이 있다.
## 검증 노트북
`notebooks/templates/08_web_ui_smoke_check.ipynb`
## 자주 나는 오류와 해결
release 화면에 내부 진단 UI가 노출되지 않게 모드를 확인한다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] `/tourism-ui/` 열림
- [ ] option builder 동작
- [ ] 카드 렌더링
