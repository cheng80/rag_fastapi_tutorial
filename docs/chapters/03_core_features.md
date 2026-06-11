# 03. 핵심 기능 재현

## 이번 장에서 만들 것

일반 RAG 채팅, 관광 상담, TourAPI 조회, 추천 카드, 출처 표시 흐름을 연결한다.

## 왜 필요한가

파일만 있으면 앱처럼 보이지만 사용자는 관광 상담 결과를 본다. 원본형 튜토리얼은 사용자가 보는 상담 흐름까지 재현해야 한다.

## 최종 폴더 상태

```text
project_template/app/services/
├─ rag_service.py
├─ retriever.py
├─ tour_api_service.py
├─ tourism_chat_service.py
├─ tourism_query_service.py
└─ tourism_card_codec.py
```

## 새로 만들 파일

- `project_template/app/services/rag_service.py`
- `project_template/app/services/tourism_chat_service.py`
- `project_template/app/services/tourism_query_service.py`
- `project_template/app/schemas/tourism.py`

## 코드 전체

```bash
cd project_template
python -m pytest tests/test_tourism_api.py tests/test_tourism_option_flow_ui.py -q
```

## 코드 흐름 설명

질문은 `/tourism/chat`으로 들어온다. `TourismQueryService`가 지역과 조건을 해석하고, `TourAPIService`가 자료를 찾고, `TourismChatService`가 답변과 카드를 만든다.

## 실행 명령

```bash
curl -i -X POST http://127.0.0.1:8000/tourism/chat \
  -H "Content-Type: application/json" \
  --data '{"message":"서울 강남구 휠체어 관광지 추천"}'
```

## 성공 기준

- 빈 메시지는 400으로 거절된다.
- 추천 카드 필드가 웹 UI와 맞다.
- 사용자 문구에 내부 구현 용어가 없다.

## 검증 노트북

- `notebooks/templates/03_api_surface_check.ipynb`
- `notebooks/executed/03_api_surface_check.ipynb`

## 자주 나는 오류와 해결

- 오류: API 예외가 내부 경로나 구현 용어를 노출한다.
- 해결: 사용자 응답에는 안내 문구만 넣고 내부 정보는 로그와 테스트에서만 다룬다.

## 다음 장으로 넘어가기 전 체크리스트

- [ ] 관광 상담 API가 동작한다.
- [ ] 추천 카드가 렌더링 가능한 구조다.
- [ ] 출처 표시가 있다.
