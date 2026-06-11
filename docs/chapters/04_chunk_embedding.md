# 04. Chunk/Embedding

## 이번 장에서 만들 것
문서를 chunk로 나누고 embedding 입력을 만든다.
## 왜 필요한가
긴 문서는 그대로 검색하기 어렵다. 적당한 chunk가 검색 단위가 된다.
## 최종 폴더 상태
`app/services/text_splitter.py`, `app/services/embedding_service.py`
## 새로 만들 파일
`text_splitter.py`, `embedding_service.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_splitter.py -q
```
## 코드 흐름 설명
splitter가 텍스트를 겹침 있는 chunk로 만들고 embedding service가 벡터 입력을 준비한다.
## 실행 명령
```bash
python -m pytest tests/test_splitter.py -q
```
## 성공 기준
chunk 개수와 내용이 예측 가능하다.
## 검증 노트북
`notebooks/templates/04_embedding_retrieval_check.ipynb`
## 자주 나는 오류와 해결
chunk가 너무 크면 검색 근거가 흐려진다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] chunk 생성
- [ ] overlap 확인
- [ ] embedding 입력 확인
