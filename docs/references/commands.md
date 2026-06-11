# 명령어 참고

## 문서 구조 검증

```bash
python3 scripts/validate_tutorial_docs.py --check all
python3 scripts/validate_tutorial_docs.py --check tutorial-book-structure
```

## 루트 검증

```bash
python -m pytest tests/test_project_template_parity.py tests/test_tutorial_docs.py -q
```

## 템플릿 앱 검증

```bash
cd project_template
python -m pytest tests/test_tourism_api.py tests/test_tourism_option_flow_ui.py -q
```

## 앱 실행

```bash
cd project_template
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## HTTP 확인

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/tourism/regions
```
