# 02. FastAPI

## 이번 장에서 만들 것
FastAPI 앱 진입점과 `/health` 라우트를 만든다.
## 왜 필요한가
가장 작은 HTTP 표면을 먼저 확인해야 뒤 장의 API 오류를 좁힐 수 있다.
## 최종 폴더 상태
`project_template/app/main.py`, `project_template/app/api/routes/health.py`
## 새로 만들 파일
`app/main.py`, `app/api/routes/health.py`
## 코드 전체
```bash
cd project_template
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
## 코드 흐름 설명
`create_app()`이 앱을 만들고 health 라우터를 등록한다.
## 실행 명령
```bash
curl -i http://127.0.0.1:8000/health
```
## 성공 기준
`/health`가 `{"status":"ok"}`를 반환한다.
## 검증 노트북
`notebooks/templates/02_fastapi_health_check.ipynb`, `notebooks/executed/02_fastapi_health_check.ipynb`
## 자주 나는 오류와 해결
404가 나오면 실행 위치와 라우터 prefix를 확인한다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] 서버 실행
- [ ] `/health` 200
- [ ] TestClient 테스트 통과
