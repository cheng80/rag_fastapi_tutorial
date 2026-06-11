# 15. 운영

## 이번 장에서 만들 것
실행 스크립트, 상태 확인, 오류 좁히기 절차를 정리한다.
## 왜 필요한가
완성 앱은 실행과 운영 검증이 가능해야 한다.
## 최종 폴더 상태
`scripts/`, `run_tourism_debug_tunnel.sh`, `run_tourism_release_tunnel.sh`
## 새로 만들 파일
운영 스크립트와 검증 명령 문서
## 코드 전체
```bash
cd project_template
./run_tourism_debug_tunnel.sh
```
## 코드 흐름 설명
debug/release 실행 스크립트는 같은 앱을 다른 관찰 수준으로 연다.
## 실행 명령
```bash
python3 scripts/validate_tutorial_docs.py --check all
```
## 성공 기준
실행 명령, 검증 명령, 흔한 오류 해결표가 문서화되어 있다.
## 검증 노트북
`notebooks/templates/01_environment_check.ipynb`, `notebooks/templates/07_eval_report_check.ipynb`
## 자주 나는 오류와 해결
긴 서버는 사용자가 볼 수 있는 터미널에서 실행한다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] debug 실행 이해
- [ ] release 실행 이해
- [ ] 오류 해결표 확인
