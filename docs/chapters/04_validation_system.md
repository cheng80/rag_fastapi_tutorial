# 04. 검증 체계 작성

## 이번 장에서 만들 것

원본 구조, API, 지역 데이터, UI, 문서 구조를 테스트와 실제 QA로 검증한다.

## 왜 필요한가

테스트만 통과해도 실제 화면이 깨질 수 있다. 이 튜토리얼은 자동 테스트와 실제 HTTP/browser 검증을 함께 사용한다.

## 최종 폴더 상태

```text
tests/
├─ test_project_template_parity.py
└─ test_tutorial_docs.py
scripts/
└─ validate_tutorial_docs.py
```

## 새로 만들 파일

- `tests/test_project_template_parity.py`
- `tests/test_tutorial_docs.py`
- `scripts/validate_tutorial_docs.py`

## 코드 전체

```bash
python -m pytest tests/test_project_template_parity.py tests/test_tutorial_docs.py -q
python3 scripts/validate_tutorial_docs.py --check all
```

## 코드 흐름 설명

테스트는 `project_template`의 구조와 사용자 표면을 확인한다. validator는 문서 구조와 사용자 화면 누수를 확인한다. 실제 QA는 HTTP와 브라우저로 수행한다.

## 실행 명령

```bash
cd project_template
python -m pytest tests/test_tourism_api.py tests/test_tourism_option_flow_ui.py -q
```

## 성공 기준

- 일부 지역 데이터만 있으면 실패한다.
- 튜토리얼 문구가 사용자 화면에 있으면 실패한다.
- README 링크와 런타임 부산물 누락/혼입을 잡는다.

## 검증 노트북

- `notebooks/templates/02_project_structure_check.ipynb`
- `notebooks/templates/03_api_surface_check.ipynb`

## 자주 나는 오류와 해결

- 오류: 테스트 실행 뒤 `__pycache__`나 Chroma DB가 산출물에 남는다.
- 해결: 검증 뒤 실행 부산물을 제거하고 스캔한다.

## 다음 장으로 넘어가기 전 체크리스트

- [ ] 자동 테스트를 실행했다.
- [ ] 실제 HTTP/browser QA를 실행했다.
- [ ] 실행 부산물을 제거했다.
