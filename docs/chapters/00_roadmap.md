# 00. 원본형 RAG FastAPI 튜토리얼 로드맵

## 이번 장에서 만들 것

이 장에서는 전체 튜토리얼북의 목표, 산출물, 검증 흐름을 정한다. 최종 목표는 작은 샘플이 아니라 원본형 `project_template` 앱을 다시 만들 수 있는 교재다.

## 왜 필요한가

초급자는 “무엇을 따라 만들고 있는지”가 먼저 보여야 한다. 원본 앱과 같은 구조를 만들되 설명은 문서에만 두는 원칙을 처음에 고정한다.

## 최종 폴더 상태

```text
docs/
├─ chapters/
├─ references/
├─ original_app_reference.md
└─ tutorial_build_original_app.md
notebooks/
├─ templates/
└─ executed/
project_template/
```

## 새로 만들 파일

- `docs/chapters/00_roadmap.md`
- `docs/references/terms.md`
- `notebooks/templates/*`
- `notebooks/executed/*`

## 코드 전체

```bash
python3 scripts/validate_tutorial_docs.py --check tutorial-book-structure
```

## 코드 흐름 설명

검증 스크립트는 장별 문서, 참고 문서, 검증 노트북이 모두 있는지 확인한다. 이 장은 나머지 장을 읽는 순서를 안내한다.

## 실행 명령

```bash
python3 scripts/validate_tutorial_docs.py --check all
```

## 성공 기준

- 장별 Markdown 문서가 있다.
- 참고 문서가 있다.
- 템플릿 노트북과 실행 완료 노트북이 있다.

## 검증 노트북

- `notebooks/templates/01_original_baseline_check.ipynb`
- `notebooks/executed/01_original_baseline_check.ipynb`

## 자주 나는 오류와 해결

- 오류: `project_template`만 만들고 교재 구조를 만들지 않는다.
- 해결: `docs/chapters`, `docs/references`, `notebooks`를 먼저 만든다.

## 다음 장으로 넘어가기 전 체크리스트

- [ ] 원본 우선 원칙을 이해했다.
- [ ] 튜토리얼 설명은 문서에만 둔다.
- [ ] 사용자 화면은 실제 앱 화면으로 남긴다.
