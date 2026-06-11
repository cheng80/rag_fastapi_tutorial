# 11. Intent/Context

## 이번 장에서 만들 것
후속 질문, 조건 강화, 지역 변경 의도를 분류한다.
## 왜 필요한가
관광 상담은 한 번의 질문보다 이어지는 대화가 많다.
## 최종 폴더 상태
`tourism_intent_classifier.py`, `tourism_context_classifier.py`
## 새로 만들 파일
`tourism_intent_classifier.py`, `tourism_context_classifier.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_tourism_intent_classifier.py tests/test_tourism_context_classifier.py -q
```
## 코드 흐름 설명
intent는 사용자의 행동을, context는 이전 질문과의 연결 방식을 판단한다.
## 실행 명령
```bash
python -m pytest tests/test_tourism_intent_classifier.py tests/test_tourism_context_classifier.py -q
```
## 성공 기준
후속 질문에서 session context가 유지된다.
## 검증 노트북
`notebooks/templates/06_tourapi_cache_fallback_check.ipynb`
## 자주 나는 오류와 해결
session_id가 바뀌면 이전 조건이 이어지지 않는다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] intent 분류
- [ ] context 분류
- [ ] session 유지
