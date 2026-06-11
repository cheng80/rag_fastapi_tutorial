# 01. 환경

## 이번 장에서 만들 것
Python 실행 환경, `.env.example`, 로컬 모델 준비 확인 흐름을 만든다.
## 왜 필요한가
환경이 흔들리면 이후 FastAPI, RAG, TourAPI 검증이 모두 다른 오류처럼 보인다.
## 최종 폴더 상태
`project_template/requirements.txt`, `project_template/.env.example`, `notebooks/templates/01_environment_check.ipynb`
## 새로 만들 파일
`project_template/.env.example`, `notebooks/templates/01_environment_check.ipynb`
## 코드 전체
```bash
cd project_template
python -m pip install -r requirements.txt
```
## 코드 흐름 설명
설정 파일은 앱 실행 전 필요한 모델, API, 캐시 경로를 한곳에서 확인하게 한다.
## 실행 명령
```bash
python3 scripts/validate_tutorial_docs.py --check tutorial-book-structure
```
## 성공 기준
필수 파일과 환경 확인 Notebook이 존재한다.
## 검증 노트북
`notebooks/templates/01_environment_check.ipynb`, `notebooks/executed/01_environment_check.ipynb`
## 자주 나는 오류와 해결
`.env`를 루트에 두지 말고 `project_template` 기준으로 관리한다.
## 다음 장으로 넘어가기 전 체크리스트
- [ ] Python 실행 가능
- [ ] `.env.example` 확인
- [ ] Notebook 검증 흐름 확인
