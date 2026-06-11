# 03. 문서 로딩

## 이번 장에서 만들 것
RAG 입력 문서를 읽고 문서 id, 제목, 본문을 확인한다.
## 왜 필요한가
검색 품질은 문서 로딩 품질에서 시작한다.
## 최종 폴더 상태
`project_template/data/raw/example_faq.md`, `project_template/app/services/document_loader.py`
## 새로 만들 파일
`app/services/document_loader.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_prompt_builder.py -q
```
## 코드 흐름 설명
원본 자료를 읽어 검색 가능한 작은 문서 객체로 정리한다.
## 실행 명령
```bash
python3 scripts/validate_tutorial_docs.py --check all
```
## 성공 기준
문서 id/title/text를 확인할 수 있다.
## 검증 노트북
`notebooks/templates/03_document_loading_check.ipynb`, `notebooks/executed/03_document_loading_check.ipynb`
## 자주 나는 오류와 해결
빈 문서가 나오면 파일 경로와 인코딩을 확인한다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] raw 문서 존재
- [ ] loader 존재
- [ ] 문서 필드 확인
