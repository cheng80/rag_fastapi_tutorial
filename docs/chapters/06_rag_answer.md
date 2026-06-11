# 06. RAG 답변

## 이번 장에서 만들 것
검색 근거를 프롬프트에 넣고 답변과 출처를 반환한다.
## 왜 필요한가
검색만으로는 사용자 응답이 되지 않는다.
## 최종 폴더 상태
`app/services/rag_service.py`, `app/services/prompt_builder.py`
## 새로 만들 파일
`rag_service.py`, `prompt_builder.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_prompt_builder.py -q
```
## 코드 흐름 설명
prompt builder가 검색 근거를 묶고 LLM service가 응답을 만든다.
## 실행 명령
```bash
python -m pytest tests/test_prompt_builder.py -q
```
## 성공 기준
answer와 sources가 함께 반환된다.
## 검증 노트북
`notebooks/templates/05_chat_api_check.ipynb`
## 자주 나는 오류와 해결
근거 없는 답변이 나오면 no-context prompt를 확인한다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] prompt 구성 확인
- [ ] source 반환
- [ ] no-context 처리
