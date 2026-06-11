# 01. 원본 기준 고정

## 이번 장에서 만들 것

원본 앱의 파일 맵, 복사 금지 대상, 목표 구조 비교표를 만든다.

## 왜 필요한가

원본 기준을 고정하지 않으면 튜토리얼 편의로 파일 구조를 줄이게 된다. 이 튜토리얼은 원본형 결과물을 만드는 교재이므로 먼저 비교 기준을 만든다.

## 최종 폴더 상태

```text
docs/
├─ original_app_reference.md
└─ chapters/01_original_baseline.md
```

## 새로 만들 파일

- `docs/original_app_reference.md`
- `docs/chapters/01_original_baseline.md`

## 코드 전체

```bash
python3 scripts/validate_tutorial_docs.py --check original-map
```

## 코드 흐름 설명

`original_app_reference.md`는 원본 앱 파일과 `project_template` 목표 위치를 나란히 적는다. `.env`, SQLite, Chroma 런타임 저장소, `data/generated`, `.venv`, `__pycache__`는 산출물에 넣지 않는다.

## 실행 명령

```bash
python3 scripts/validate_tutorial_docs.py --check original-map
```

## 성공 기준

- 원본 앱 파일 맵이 있다.
- 복사 금지 대상이 있다.
- 목표 구조 비교표가 있다.

## 검증 노트북

- `notebooks/templates/01_original_baseline_check.ipynb`
- `notebooks/executed/01_original_baseline_check.ipynb`

## 자주 나는 오류와 해결

- 오류: 개인 경로나 비밀값을 문서에 그대로 쓴다.
- 해결: `<original_app_root>`처럼 치환 가능한 이름을 사용한다.

## 다음 장으로 넘어가기 전 체크리스트

- [ ] 원본 기준 파일을 확인했다.
- [ ] 복사 금지 대상을 확인했다.
- [ ] 목표 구조를 비교할 수 있다.
