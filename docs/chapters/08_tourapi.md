# 08. TourAPI

## 이번 장에서 만들 것
TourAPI 조회 설정과 서비스 계층을 만든다.
## 왜 필요한가
관광 상담 앱은 최신 관광 데이터와 준비된 자료를 함께 사용한다.
## 최종 폴더 상태
`app/services/tour_api_service.py`, `app/core/config.py`
## 새로 만들 파일
`tour_api_service.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_tour_api_service.py -q
```
## 코드 흐름 설명
설정에서 API base URL과 key를 읽고 service가 endpoint 호출을 담당한다.
## 실행 명령
```bash
python -m pytest tests/test_tour_api_service.py -q
```
## 성공 기준
API key가 없어도 안전한 fallback 흐름을 배울 수 있다.
## 검증 노트북
`notebooks/templates/06_tourapi_cache_fallback_check.ipynb`
## 자주 나는 오류와 해결
키가 없을 때 실패가 아니라 준비된 자료 흐름으로 확인한다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] key 비노출
- [ ] timeout 설정
- [ ] fallback 준비
