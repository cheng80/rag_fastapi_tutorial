# 오류 해결표

## `project_template app entrypoint missing`

`project_template/app/main.py`가 없거나 `project_template` 구조가 아직 이식되지 않은 상태다. 원본 앱의 `app/` 구조를 먼저 맞춘다.

## 지역 수가 17개가 아니다

전국 지역 데이터가 아니라 일부 샘플만 들어간 상태다. `data/processed/tour_area_codes.json`을 원본 기준으로 확인한다.

## 사용자 화면에 튜토리얼 문구가 보인다

문서에 있어야 할 설명이 `frontend/web/index.html`이나 API 응답으로 들어간 상태다. 설명은 `docs/`로 옮기고 사용자 화면은 관광 상담 앱으로 유지한다.

## README 링크가 깨진다

`project_template/README.md`가 가리키는 로컬 문서가 복사되지 않은 상태다. 링크 대상 문서를 함께 넣거나 README 링크를 제거한다.

## 실행 뒤 DB나 pycache가 생긴다

테스트나 서버 실행 부산물이다. 산출물에 포함하지 말고 검증 뒤 삭제한다.
