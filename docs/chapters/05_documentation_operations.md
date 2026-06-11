# 05. 튜토리얼 문서 운영

## 이번 장에서 만들 것

장별 문서, 참고 문서, 검증 노트북을 유지하는 운영 규칙을 만든다.

## 왜 필요한가

앱 구조가 바뀌면 교재도 같이 바뀌어야 한다. 문서가 진행 보고서가 아니라 초급자가 따라 할 수 있는 교재로 남게 관리한다.

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
```

## 새로 만들 파일

- `docs/references/terms.md`
- `docs/references/commands.md`
- `docs/references/troubleshooting.md`
- `docs/references/production_mapping.md`

## 코드 전체

```bash
python3 scripts/validate_tutorial_docs.py --check tutorial-book-structure
```

## 코드 흐름 설명

장별 문서는 학습 순서를 제공한다. 참고 문서는 용어와 명령을 빠르게 찾게 한다. 노트북은 검증 과정을 눈으로 확인하는 보조 증거다.

## 실행 명령

```bash
python -m pytest tests/test_tutorial_docs.py -q
```

## 성공 기준

- 모든 장이 같은 교재 형식을 따른다.
- 참고 문서 네 개가 있다.
- 템플릿 노트북과 실행 완료 노트북이 짝으로 있다.

## 검증 노트북

- `notebooks/templates/01_original_baseline_check.ipynb`
- `notebooks/executed/01_original_baseline_check.ipynb`

## 자주 나는 오류와 해결

- 오류: 장별 문서와 통합 문서 내용이 서로 다르다.
- 해결: `docs/tutorial_build_original_app.md`는 요약본, `docs/chapters/*`는 따라 하는 본문으로 역할을 나눈다.

## 다음 장으로 넘어가기 전 체크리스트

- [ ] references 문서를 확인했다.
- [ ] notebooks 템플릿과 실행본이 있다.
- [ ] validator가 전체 구조를 통과한다.
