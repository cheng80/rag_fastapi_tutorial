# Tutorial Notebooks

이 폴더는 튜토리얼북 검증용 Jupyter Notebook을 보관한다.

## 구조

- `templates/`: 작성 전 또는 실행 전 템플릿
- `executed/`: 실제 실행이 끝난 검증 산출물

## 원칙

- 노트북은 설명용이 아니라 검증용이다.
- 각 노트북은 실행 전제, 성공 조건, 실패 시 확인할 항목을 포함한다.
- API 키가 필요한 live TourAPI 검증은 optional cell로 분리한다.
- fallback-only 검증은 API 키 없이도 실행되어야 한다.
