# 05. Chroma 검색

## 이번 장에서 만들 것
벡터 저장소 검색 흐름을 만든다.
## 왜 필요한가
RAG 답변은 검색 근거가 있어야 신뢰할 수 있다.
## 최종 폴더 상태
`app/services/vector_store.py`, `app/services/retriever.py`
## 새로 만들 파일
`vector_store.py`, `retriever.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_retriever.py -q
```
## 코드 흐름 설명
retriever는 query embedding으로 관련 chunk를 찾고 RAG service에 넘긴다.
## 실행 명령
```bash
python -m pytest tests/test_retriever.py -q
```
## 성공 기준
검색 결과에 source와 score가 있다.
## 검증 노트북
`notebooks/templates/04_embedding_retrieval_check.ipynb`
## 자주 나는 오류와 해결
런타임 Chroma DB는 산출물에 포함하지 않는다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] retriever 테스트
- [ ] runtime DB 제외
- [ ] source 반환 확인
