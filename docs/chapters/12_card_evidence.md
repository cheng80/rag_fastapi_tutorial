# 12. Card Evidence

## 이번 장에서 만들 것
추천 카드와 근거 정책을 만든다.
## 왜 필요한가
접근성 정보는 근거 없이 생성하면 위험하다.
## 최종 폴더 상태
`app/services/tourism_card_codec.py`, `app/schemas/tourism.py`
## 새로 만들 파일
`tourism_card_codec.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_tourism_chat_service.py -q
```
## 코드 흐름 설명
card codec은 raw field와 출처를 유지하면서 웹 UI가 그릴 수 있는 카드로 바꾼다.
## 실행 명령
```bash
python -m pytest tests/test_tourism_chat_service.py -q
```
## 성공 기준
카드에 title, reason, tags, sources가 있다.
## 검증 노트북
`notebooks/templates/06_tourapi_cache_fallback_check.ipynb`
## 자주 나는 오류와 해결
없는 접근성 정보를 추정하지 않는다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] raw evidence 확인
- [ ] source 표시
- [ ] card schema 확인
