# 10. 지역/조건 파싱

## 이번 장에서 만들 것
지역, 시군구, 조건, 선호, 제외 의도를 추출한다.
## 왜 필요한가
`강남구` 같은 짧은 질문도 TourAPI 코드로 연결되어야 한다.
## 최종 폴더 상태
`app/services/tourism_query_service.py`, `data/processed/tour_area_codes.json`
## 새로 만들 파일
`tourism_query_service.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_tourism_query_service.py -q
```
## 코드 흐름 설명
query service가 자연어에서 지역과 조건을 뽑아 검색 조건으로 바꾼다.
## 실행 명령
```bash
python -m pytest tests/test_tourism_query_service.py -q
```
## 성공 기준
서울/부산/인천 중구를 구분하고 강남구/해운대구/제주시를 해석한다.
## 검증 노트북
`notebooks/templates/06_tourapi_cache_fallback_check.ipynb`
## 자주 나는 오류와 해결
동명이인 시군구는 광역 지역과 함께 확인한다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] 17개 광역
- [ ] 시군구 목록
- [ ] ambiguous alias 확인
