# 13. Eval/Event

## 이번 장에서 만들 것
평가 질문, query event, replay 흐름을 만든다.
## 왜 필요한가
관광 상담 품질은 반복 질문 세트로 확인해야 한다.
## 최종 폴더 상태
`data/eval/*.jsonl`, `tourism_query_event_logger.py`
## 새로 만들 파일
`tourism_query_event_logger.py`
## 코드 전체
```bash
cd project_template
python -m pytest tests/test_tourism_quality_regression.py tests/test_tourism_query_event_logger.py -q
```
## 코드 흐름 설명
event logger는 질의와 결과를 남기고 eval은 회귀 품질을 확인한다.
## 실행 명령
```bash
python -m pytest tests/test_tourism_quality_regression.py -q
```
## 성공 기준
평가 파일과 이벤트 로그 테스트가 있다.
## 검증 노트북
`notebooks/templates/07_eval_report_check.ipynb`
## 자주 나는 오류와 해결
개인 질문 원문을 로그에 넣지 않도록 설정을 확인한다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] eval data 확인
- [ ] event logger 확인
- [ ] message include 정책 확인
