# 02. 원본 구조 이식

## 이번 장에서 만들 것

원본 앱의 FastAPI, 서비스, 웹 UI, 데이터 구조를 `project_template`에 이식한다.

## 왜 필요한가

초급자 설명을 위해 구조를 단순화하면 원본 앱과 다른 결과물이 된다. 실제 산출물은 원본 구조를 유지하고 설명만 단계적으로 쓴다.

## 최종 폴더 상태

```text
project_template/
├─ app/
├─ data/
├─ frontend/
├─ scripts/
├─ tests/
├─ requirements.txt
└─ README.md
```

## 새로 만들 파일

- `project_template/app/main.py`
- `project_template/app/api/deps.py`
- `project_template/frontend/web/index.html`
- `project_template/data/processed/tour_area_codes.json`

## 코드 전체

```bash
cd project_template
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 코드 흐름 설명

`app/main.py`는 앱을 만들고 라우터를 붙인다. `frontend/web`은 `/tourism-ui/`로 연결된다. 지역 데이터는 `/tourism/regions`에서 읽힌다.

## 실행 명령

```bash
cd project_template
python -m pytest tests/test_tourism_api.py -q
```

## 성공 기준

- `/health`가 200을 반환한다.
- `/tourism/regions`가 전국 17개 광역 지역을 반환한다.
- `/tourism-ui/`가 열린다.

## 검증 노트북

- `notebooks/templates/02_project_structure_check.ipynb`
- `notebooks/executed/02_project_structure_check.ipynb`

## 자주 나는 오류와 해결

- 오류: `PROJECT_ROOT`가 원본 프로젝트를 가리킨다.
- 해결: `project_template/app/core/config.py`의 기준 경로가 `project_template` 내부인지 확인한다.

## 다음 장으로 넘어가기 전 체크리스트

- [ ] 앱 구조가 원본과 대응된다.
- [ ] 웹 UI 파일 네 개가 있다.
- [ ] 전국 지역 데이터가 있다.
