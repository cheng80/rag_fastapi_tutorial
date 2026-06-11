# 07. Chat API

## 이번 장에서 만들 것
`/chat` API payload와 session 흐름을 만든다.
## 왜 필요한가
웹과 외부 호출은 API 계약을 기준으로 앱을 사용한다.
## 최종 폴더 상태
`app/api/routes/chat.py`, `app/schemas/chat.py`
## 새로 만들 파일
`chat.py`, `schemas/chat.py`
## 코드 전체
```bash
curl -i -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" --data '{"message":"질문"}'
```
## 코드 흐름 설명
route가 request schema를 받고 RAG service로 넘긴다.
## 실행 명령
```bash
cd project_template
python -m pytest tests/test_tourism_api.py -q
```
## 성공 기준
빈 payload는 거절되고 정상 payload는 답변한다.
## 검증 노트북
`notebooks/templates/05_chat_api_check.ipynb`
## 자주 나는 오류와 해결
422/400 차이는 schema 오류와 비즈니스 검증 오류를 나눠 본다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] request schema
- [ ] response schema
- [ ] session_id 확인
