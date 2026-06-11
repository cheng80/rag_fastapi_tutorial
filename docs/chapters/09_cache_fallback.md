# 09. Cache/Fallback

## 이번 장에서 만들 것
TourAPI 실패나 지연 시 캐시와 준비된 자료 응답 흐름을 만든다.
## 왜 필요한가
외부 API는 항상 빠르고 안정적이지 않다.
## 최종 폴더 상태
`app/services/tour_api_response_cache.py`, `data/generated/.gitkeep`
## 새로 만들 파일
`tour_api_response_cache.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_manage_tour_api_response_cache.py -q
```
## 코드 흐름 설명
cache-first 전략은 저장된 응답을 먼저 보고 필요할 때 live 조회를 시도한다.
## 실행 명령
```bash
python -m pytest tests/test_manage_tour_api_response_cache.py -q
```
## 성공 기준
런타임 cache DB는 산출물에 포함하지 않는다.
## 검증 노트북
`notebooks/templates/06_tourapi_cache_fallback_check.ipynb`
## 자주 나는 오류와 해결
cache sqlite를 커밋하지 않는다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] cache path 확인
- [ ] fallback 응답 확인
- [ ] runtime 파일 제외
