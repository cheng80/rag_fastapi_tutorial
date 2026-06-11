# Original App Parity Project Template

## TL;DR
> Summary:      Finish `project_template/` as a source-faithful FastAPI/RAG/tourism/web/data/test template from `<original_app_root>` while removing runtime artifacts and protecting the repo from secrets, generated stores, cache files, and machine-specific paths.
> Deliverables:
> - `project_template/` with original-style backend, RAG, tourism, web UI, data, scripts, and tests.
> - Root parity/safety tests that fail before any missing or forbidden surface is fixed.
> - Tutorial/docs updates that explain how to build the original-shaped app without changing the app surface into tutorial copy.
> - `.omo/evidence/` RED/GREEN and manual-QA artifacts for every task.
> Effort:       Large
> Risk:         High - cross-surface parity plus large static data/scripts can accidentally ship generated artifacts, secrets, or user-facing internal terms.

## Scope
### Must have
- Preserve existing untracked user/worktree content unless a task explicitly replaces it with verified source-parity content; current `project_template/` is treated as WIP, not disposable.
- Use `<original_app_root>` as `../chatbot_rag` when running from this repo root; do not write machine-specific absolute paths into project files.
- Reproduce the source app structure described in `docs/original_first_tutorial_plan.md:17`, `docs/original_first_tutorial_plan.md:87`, and `docs/original_first_tutorial_plan.md:118`.
- Keep FastAPI router/static mounting behavior aligned with `../chatbot_rag/app/main.py:9`, `../chatbot_rag/app/main.py:26`, and `../chatbot_rag/app/main.py:31`.
- Keep dependency assembly aligned with `../chatbot_rag/app/api/deps.py:25`, `../chatbot_rag/app/api/deps.py:62`, `../chatbot_rag/app/api/deps.py:87`, and `../chatbot_rag/app/api/deps.py:102`.
- Preserve user-facing API contracts from `../chatbot_rag/app/api/routes/health.py:6`, `../chatbot_rag/app/api/routes/chat.py:10`, `../chatbot_rag/app/api/routes/tourism.py:36`, `../chatbot_rag/app/api/routes/tourism.py:60`, and `../chatbot_rag/app/api/routes/documents.py:11`.
- Provide nationwide tourism region data: 17 area units, full sigungu lookup, ambiguous aliases such as `중구`, and direct resolution for `강남구`, `해운대구`, `유성구`, and `제주시`; source data references include `../chatbot_rag/data/processed/tour_area_codes.json:3`, `../chatbot_rag/data/processed/tour_area_codes.json:325`, `../chatbot_rag/data/processed/tour_area_codes.json:901`, `../chatbot_rag/data/processed/tour_area_codes.json:2839`, and `../chatbot_rag/data/processed/tour_area_codes.json:2887`.
- Keep tourism conversation behavior aligned with `../chatbot_rag/app/services/tourism_chat_service.py:325`, including clarification, unsupported scope, live/cache/indexed/sample lookup order, session follow-ups, suggestions, and cards.
- Keep web UI surface aligned with `../chatbot_rag/frontend/web/index.html:10`, `../chatbot_rag/frontend/web/index.html:99`, `../chatbot_rag/frontend/web/index.html:147`, `../chatbot_rag/frontend/web/index.html:254`, `../chatbot_rag/frontend/web/index.html:296`, `../chatbot_rag/frontend/web/app.js:252`, `../chatbot_rag/frontend/web/app.js:327`, and `../chatbot_rag/frontend/web/option_flow_builder.js:34`.
- Tests must be written first for each implementation task, with RED output captured before production/template changes and GREEN output captured after.
- Manual QA must use bounded processes with cleanup receipts; do not start hidden long-running servers except bounded QA servers that are killed and verified.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Do not commit `.env`, local secrets, local SQLite DBs, vector-store runtime files, `.venv`, `.pytest_cache`, `__pycache__`, logs, or generated run artifacts; this is required by `docs/original_first_tutorial_plan.md:65` and `docs/original_first_tutorial_plan.md:268`.
- Do not remove or revert unrelated untracked `.agents/`, `.omo/`, `AGENTS.md`, `data/generated/nanobanana-images/images.db`, existing WIP `project_template/`, or existing `tests/` content; only modify files required by the plan.
- Do not expose `Chroma`, `top_k`, `lookup_mode`, `fallback`, `debug`, `pipeline`, or `parity` in visible user UI/API response text; internal diagnostics/tests/docs may mention them as allowed by `docs/original_first_tutorial_plan.md:81` and `docs/original_first_tutorial_plan.md:162`.
- Do not simplify the original app into a toy tutorial app; tutorial explanation belongs in docs only per `docs/original_first_tutorial_plan.md:5` and `docs/original_first_tutorial_plan.md:116`.
- Do not add machine-specific absolute or home-relative local paths to project code, docs, examples, prompts, or tests; root rule is `AGENTS.md:81`.
- Do not run Cloudflare tunnel scripts during automated QA; only syntax-check them and document that they must be run in a visible terminal per `AGENTS.md:77`.
- Do not add unrelated frontend redesign, Flutter app work, external deployment, model training, or real TourAPI calls requiring secrets.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD + pytest for Python/FastAPI/data/docs, node subprocess checks for `frontend/web/option_flow_builder.js`, bash syntax checks for scripts, and Playwright real-Chrome browser QA for `/tourism-ui/`.
- QA policy: every task has agent-executed scenarios
- Evidence: `.omo/evidence/task-<N>-<slug>.<ext>`

Concrete ULW success criteria:
- SC1 Backend/API parity: RED test `tests/test_project_template_api_contract.py::test_project_template_health_regions_chat_contract` fails before missing/incorrect API surface; GREEN after fixes; manual HTTP QA captures `/health`, `/tourism/regions`, blank `/tourism/chat`, and sample `/tourism/chat` responses in `.omo/evidence/task-11-api-http.txt`.
- SC2 Data/query parity: RED test `project_template/tests/test_tourism_quality_regression.py::test_quality_region_extraction_matrix` or added `tests/test_project_template_region_data.py::test_project_template_has_nationwide_region_index` fails before complete region data; GREEN after fixes; manual tmux QA captures parsed 17-area/422-region summary in `.omo/evidence/task-5-region-data.txt`.
- SC3 Web UI parity/no internal visible terms: RED test `tests/test_project_template_web_contract.py::test_release_ui_has_original_controls_without_forbidden_visible_text` fails before UI parity; GREEN after fixes; manual browser QA captures release-mode screenshot and action log in `.omo/evidence/task-12-release-ui.png` and `.omo/evidence/task-12-release-ui.log`.
- SC4 Artifact hygiene: RED test `tests/test_project_template_hygiene.py::test_project_template_excludes_runtime_artifacts` fails while generated/runtime artifacts are present; GREEN after cleanup/ignore rules; manual tmux QA captures `find` output proving no forbidden files under `project_template/` in `.omo/evidence/task-1-hygiene.txt`.

Concrete verification matrix:
| Criterion | Test written first | RED evidence | GREEN evidence | Manual-QA channel | Manual artifact |
|-----------|--------------------|--------------|----------------|-------------------|-----------------|
| SC1 API parity | `tests/test_project_template_api_contract.py::test_project_template_health_regions_chat_contract` | `.omo/evidence/task-11-api-red.txt` | `.omo/evidence/task-11-api-green.txt` | HTTP call | `.omo/evidence/task-11-api-http.txt` |
| SC2 region/query parity | `tests/test_project_template_region_data.py::test_project_template_has_nationwide_region_index` | `.omo/evidence/task-5-region-red.txt` | `.omo/evidence/task-5-region-green.txt` | tmux | `.omo/evidence/task-5-region-data.txt` |
| SC3 web UI parity | `tests/test_project_template_web_contract.py::test_release_ui_has_original_controls_without_forbidden_visible_text` | `.omo/evidence/task-9-web-red.txt` | `.omo/evidence/task-9-web-green.txt` | playwright(real Chrome) | `.omo/evidence/task-12-release-ui.png`, `.omo/evidence/task-12-release-ui.log` |
| SC4 artifact hygiene | `tests/test_project_template_hygiene.py::test_project_template_excludes_runtime_artifacts` | `.omo/evidence/task-1-hygiene-red.txt` | `.omo/evidence/task-1-hygiene-green.txt` | tmux | `.omo/evidence/task-1-hygiene.txt` |

External references:
- FastAPI APIRouter reference: `https://fastapi.tiangolo.com/reference/apirouter/`
- FastAPI bigger applications/multiple files: `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
- FastAPI testing/TestClient: `https://fastapi.tiangolo.com/tutorial/testing/`
- FastAPI static files: `https://fastapi.tiangolo.com/tutorial/static-files/`
- pytest temporary paths: `https://docs.pytest.org/en/stable/how-to/tmp_path.html`
- Playwright screenshots: `https://playwright.dev/docs/screenshots`
- Playwright Python library/browser use: `https://playwright.dev/python/docs/library`

Context-gathering note: read-only subagent lanes were attempted but produced no deliverables because the configured Codex model names were unsupported in this account. This plan is based on direct source/target inspection and official docs above.

## Execution strategy
### Parallel execution waves
> Target 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks to maximize parallelism.

Wave 1 (no dependencies):
- Task 1: Guard hygiene, ignore rules, and forbidden-artifact tests
- Task 2: Source parity manifest and copy policy
- Task 3: Template dependency/runtime/test bootstrap

Wave 2 (after Wave 1):
- Task 4: Backend app/router/schema parity depends [1, 2, 3]
- Task 5: Nationwide data and query extraction parity depends [1, 2, 3]
- Task 6: RAG services, repositories, prompts, and document scripts depends [1, 2, 3]
- Task 7: Tourism chat, TourAPI adapters, cache, and event logging depends [1, 2, 3, 5]
- Task 8: Static raw/eval corpus and utility scripts depends [1, 2, 3]

Wave 3 (after Wave 2):
- Task 9: Web UI and option-flow parity depends [4, 5, 7]
- Task 10: Migrated source test suite and parity tests depends [4, 5, 6, 7, 8, 9]
- Task 11: Bounded API runtime QA harness depends [4, 5, 6, 7, 8, 10]
- Task 12: Tutorial docs, README, and browser QA depends [4, 5, 7, 9, 10, 11]

Critical path: Task 1 -> Task 5 -> Task 7 -> Task 10 -> Task 11 -> Task 12

### Dependency matrix
| Task | Depends on | Blocks | Can parallelize with |
|------|------------|--------|----------------------|
| 1    | none       | 4, 5, 6, 7, 8, 10, 11, 12 | 2, 3 |
| 2    | none       | 4, 5, 6, 7, 8, 9, 10, 12 | 1, 3 |
| 3    | none       | 4, 5, 6, 7, 8, 10, 11 | 1, 2 |
| 4    | 1, 2, 3    | 9, 10, 11, 12 | 5, 6, 8 |
| 5    | 1, 2, 3    | 7, 9, 10, 11, 12 | 4, 6, 8 |
| 6    | 1, 2, 3    | 10, 11 | 4, 5, 8 |
| 7    | 1, 2, 3, 5 | 9, 10, 11, 12 | 4, 6, 8 after 5 |
| 8    | 1, 2, 3    | 10, 11 | 4, 5, 6 |
| 9    | 4, 5, 7    | 10, 12 | none in same files |
| 10   | 4, 5, 6, 7, 8, 9 | 11, 12 | none |
| 11   | 4, 5, 6, 7, 8, 10 | 12 | none |
| 12   | 4, 5, 7, 9, 10, 11 | final verification | none |

## Todos
> Implementation + Test = ONE task. Never separate.
> Every task MUST have: References + Acceptance Criteria + QA Scenarios + Commit.

- [ ] 1. Guard hygiene, ignore rules, and forbidden-artifact tests

  What to do: Write failing tests that reject forbidden runtime artifacts under `project_template/`, root-level accidental generated artifacts, machine-specific absolute paths in committed project files, and visible user-surface internal terms. Then add/update `.gitignore` and remove only forbidden artifacts inside `project_template/` if present. Keep `project_template/data/generated/.gitkeep` only if the directory is intentionally empty. Do not remove user-owned untracked `.agents/`, `.omo/`, `AGENTS.md`, or root `data/generated/nanobanana-images/images.db`.
  Must NOT do: Do not delete existing source/template code or data to make the test pass; do not remove unrelated untracked files; do not hide failures by broadening ignore rules beyond the excluded artifact classes.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [4, 5, 6, 7, 8, 10, 11, 12] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `docs/original_first_tutorial_plan.md:65` - copy exclusions for secrets, SQLite DB, Chroma store, generated files, `.venv`, and caches.
  - Pattern:  `docs/original_first_tutorial_plan.md:268` - final forbidden list.
  - Pattern:  `AGENTS.md:81` - repository-relative path rule.
  - Pattern:  `../chatbot_rag/.gitignore:142` - source ignore categories for Python/cache/runtime data.
  - Test:     `tests/test_project_template_parity.py:12` - current internal-term guard pattern to extend.
  - External: `https://docs.pytest.org/en/stable/how-to/tmp_path.html` - isolated temporary filesystem checks.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_hygiene.py::test_project_template_excludes_runtime_artifacts`; run `mkdir -p .omo/evidence && pytest tests/test_project_template_hygiene.py::test_project_template_excludes_runtime_artifacts -q | tee .omo/evidence/task-1-hygiene-red.txt` and confirm it fails for a real forbidden artifact or missing guard.
  - [ ] Write `tests/test_project_template_hygiene.py::test_project_files_use_relative_paths`; run `pytest tests/test_project_template_hygiene.py::test_project_files_use_relative_paths -q | tee .omo/evidence/task-1-paths-red.txt` and confirm it fails before path-safety coverage is implemented or before any existing violations are fixed.
  - [ ] Implement `.gitignore`/cleanup safeguards; run `pytest tests/test_project_template_hygiene.py::test_project_template_excludes_runtime_artifacts -q | tee .omo/evidence/task-1-hygiene-green.txt` and confirm it passes.
  - [ ] Run `pytest tests/test_project_template_hygiene.py::test_project_files_use_relative_paths -q | tee .omo/evidence/task-1-paths-green.txt` and confirm it passes.
  - [ ] Run `find project_template -type f \( -name '*.pyc' -o -name '*.db' -o -name '*.sqlite3' -o -path '*/.pytest_cache/*' -o -path '*/__pycache__/*' \) -print | tee .omo/evidence/task-1-forbidden-files.txt` and confirm the output is empty.

  QA scenarios (MANDATORY - task incomplete without these):
  > Name the exact tool AND its exact invocation - not "verify it works". Browser use: use Chrome to drive the page; if Chrome is not available, download and use agent-browser (https://github.com/vercel-labs/agent-browser). Computer use: OS-level GUI automation for a non-browser desktop app.
  ```
  Scenario: forbidden runtime artifacts are absent
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-1; tmux send-keys -t ulw-qa-task-1 'cd project_template && find . -type f \( -name "*.pyc" -o -name "*.db" -o -name "*.sqlite3" -o -path "*/.pytest_cache/*" -o -path "*/__pycache__/*" \) -print; echo TASK1_DONE' C-m; sleep 1; tmux capture-pane -pt ulw-qa-task-1 -S -200 > .omo/evidence/task-1-hygiene.txt; tmux kill-session -t ulw-qa-task-1
    Expected: .omo/evidence/task-1-hygiene.txt contains TASK1_DONE and no forbidden file paths.
    Evidence: .omo/evidence/task-1-hygiene.txt

  Scenario: root generated user artifact remains untouched
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-1-root; tmux send-keys -t ulw-qa-task-1-root 'test -f data/generated/nanobanana-images/images.db && echo ROOT_ARTIFACT_PRESERVED' C-m; sleep 1; tmux capture-pane -pt ulw-qa-task-1-root -S -80 > .omo/evidence/task-1-hygiene-root.txt; tmux kill-session -t ulw-qa-task-1-root
    Expected: .omo/evidence/task-1-hygiene-root.txt contains ROOT_ARTIFACT_PRESERVED.
    Evidence: .omo/evidence/task-1-hygiene-root.txt
  ```

  Commit: YES | Message: `test(template): 런타임 산출물 제외 규칙을 고정한다` | Files: [`.gitignore`, `tests/test_project_template_hygiene.py`, `project_template/**`]

- [ ] 2. Source parity manifest and copy policy

  What to do: Add a source-map document and a machine-checkable manifest that classify source files into include, exclude, and regenerate buckets. The manifest must use relative source references (`../chatbot_rag/...`) and must cover `app/`, `frontend/web/`, `data/processed/`, `data/raw/tourism_accessible/`, `data/eval/`, `scripts/`, tests, requirements, Docker, and tunnel scripts. Add tests that compare required included paths against source and target without copying excluded artifacts.
  Must NOT do: Do not add machine-specific absolute paths; do not classify runtime DB/vector-store/cache files as include; do not make the manifest a vague checklist.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [4, 5, 6, 7, 8, 9, 10, 12] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `docs/original_first_tutorial_plan.md:17` - baseline source file map.
  - Pattern:  `docs/original_first_tutorial_plan.md:188` - Step 1 requires original map and copy/no-copy split.
  - Pattern:  `docs/original_first_tutorial_plan.md:277` - first checklist requires original file map before app work.
  - Pattern:  `../chatbot_rag/app/main.py:1` - app entrypoint source.
  - Pattern:  `../chatbot_rag/frontend/web/index.html:1` - web UI source.
  - Pattern:  `../chatbot_rag/.env.example:1` - example-only env file source.
  - Test:     `tests/test_project_template_parity.py:37` - import target app from `project_template`.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_original_source_manifest.py::test_manifest_required_paths_exist_in_source_and_template`; run `pytest tests/test_original_source_manifest.py::test_manifest_required_paths_exist_in_source_and_template -q | tee .omo/evidence/task-2-manifest-red.txt` and confirm RED before all manifest/template path gaps are fixed.
  - [ ] Implement `docs/original_app_file_map.md` and `docs/original_app_manifest.json`; run `pytest tests/test_original_source_manifest.py::test_manifest_required_paths_exist_in_source_and_template -q | tee .omo/evidence/task-2-manifest-green.txt`.
  - [ ] Run `pytest tests/test_project_template_hygiene.py::test_project_files_use_relative_paths -q | tee .omo/evidence/task-2-relative-paths.txt` and confirm no machine-specific path hits outside intentionally quoted test fixtures.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: manifest maps source to target using relative paths
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-2; tmux send-keys -t ulw-qa-task-2 'jq -r ".include[].target" docs/original_app_manifest.json | sort | sed -n "1,80p"; echo TASK2_DONE' C-m; sleep 1; tmux capture-pane -pt ulw-qa-task-2 -S -200 > .omo/evidence/task-2-manifest.txt; tmux kill-session -t ulw-qa-task-2
    Expected: .omo/evidence/task-2-manifest.txt contains TASK2_DONE plus required target paths such as project_template/app/main.py and project_template/frontend/web/index.html.
    Evidence: .omo/evidence/task-2-manifest.txt

  Scenario: manifest rejects excluded runtime classes
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-2-exclude; tmux send-keys -t ulw-qa-task-2-exclude 'jq -e ".exclude[] | select(.reason|test(\"runtime|secret|generated|cache\"))" docs/original_app_manifest.json >/dev/null && echo EXCLUDES_RECORDED' C-m; sleep 1; tmux capture-pane -pt ulw-qa-task-2-exclude -S -80 > .omo/evidence/task-2-manifest-excludes.txt; tmux kill-session -t ulw-qa-task-2-exclude
    Expected: .omo/evidence/task-2-manifest-excludes.txt contains EXCLUDES_RECORDED.
    Evidence: .omo/evidence/task-2-manifest-excludes.txt
  ```

  Commit: YES | Message: `docs(template): 원본 파일 맵과 이식 정책을 기록한다` | Files: [`docs/original_app_file_map.md`, `docs/original_app_manifest.json`, `tests/test_original_source_manifest.py`]

- [ ] 3. Template dependency/runtime/test bootstrap

  What to do: Ensure `project_template/` has a reproducible Python test/runtime setup matching the source app: `requirements.txt`, `.env.example`, pytest import path behavior, and a minimal README command section. Add root tests that can import `project_template/app/main.py` from a clean subprocess without relying on the parent repo import state.
  Must NOT do: Do not create `.venv`; do not run package installation as part of committed code; do not introduce uvicorn background processes outside bounded QA.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [4, 5, 6, 7, 8, 10, 11] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `../chatbot_rag/requirements.txt:1` - source dependency list.
  - Pattern:  `../chatbot_rag/.env.example:1` - safe example env variables.
  - Pattern:  `../chatbot_rag/tests/conftest.py:1` - test import path pattern.
  - Pattern:  `../chatbot_rag/README.md:130` - source setup commands; rewrite to be template-relative.
  - External: `https://fastapi.tiangolo.com/tutorial/testing/` - TestClient usage.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_bootstrap.py::test_template_app_imports_in_clean_subprocess`; run `pytest tests/test_project_template_bootstrap.py::test_template_app_imports_in_clean_subprocess -q | tee .omo/evidence/task-3-bootstrap-red.txt` and confirm RED before import/runtime gaps are fixed.
  - [ ] Implement/fix `project_template/requirements.txt`, `project_template/.env.example`, `project_template/tests/conftest.py`, and bootstrap docs; run `pytest tests/test_project_template_bootstrap.py::test_template_app_imports_in_clean_subprocess -q | tee .omo/evidence/task-3-bootstrap-green.txt`.
  - [ ] Run `cd project_template && python -m compileall -q app tests && cd .. && echo compileall-ok | tee .omo/evidence/task-3-compileall.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: template imports app from its own root
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-3; tmux send-keys -t ulw-qa-task-3 'cd project_template && python -c "from app.main import app; print(app.title); print([r.path for r in app.routes if r.path in {\"/health\",\"/chat\",\"/tourism/chat\",\"/tourism/regions\"}])"; echo TASK3_DONE' C-m; sleep 2; tmux capture-pane -pt ulw-qa-task-3 -S -200 > .omo/evidence/task-3-bootstrap.txt; tmux kill-session -t ulw-qa-task-3
    Expected: .omo/evidence/task-3-bootstrap.txt contains TASK3_DONE, the app title, and the four expected routes.
    Evidence: .omo/evidence/task-3-bootstrap.txt

  Scenario: example environment contains placeholders only
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-3-env; tmux send-keys -t ulw-qa-task-3-env 'cd project_template && test -f .env.example && ! rg -n "=[A-Za-z0-9_-]{24,}" .env.example; echo ENV_PLACEHOLDERS_ONLY' C-m; sleep 1; tmux capture-pane -pt ulw-qa-task-3-env -S -120 > .omo/evidence/task-3-env.txt; tmux kill-session -t ulw-qa-task-3-env
    Expected: .omo/evidence/task-3-env.txt contains ENV_PLACEHOLDERS_ONLY and no secret-looking values.
    Evidence: .omo/evidence/task-3-env.txt
  ```

  Commit: YES | Message: `build(template): 실행과 테스트 부트스트랩을 맞춘다` | Files: [`project_template/requirements.txt`, `project_template/.env.example`, `project_template/tests/conftest.py`, `project_template/README.md`, `tests/test_project_template_bootstrap.py`]

- [ ] 4. Backend app/router/schema parity

  What to do: Write failing API contract tests, then sync `project_template/app/main.py`, `app/api/deps.py`, `app/api/routes/*.py`, `app/core/*.py`, `app/schemas/*.py`, repositories, and package markers with the original. Ensure `/tourism-ui/` static mount is present, route prefixes match source, and tourism/chat exceptions hide internal details.
  Must NOT do: Do not leak raw exceptions from `/tourism/chat`; do not change public response schema names; do not remove diagnostic fields from API JSON if the web uses them internally.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [9, 10, 11, 12] | Blocked by: [1, 2, 3]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `../chatbot_rag/app/main.py:9` - app factory and metadata.
  - Pattern:  `../chatbot_rag/app/main.py:26` - router prefixes.
  - Pattern:  `../chatbot_rag/app/main.py:31` - `/tourism-ui` static mount.
  - Pattern:  `../chatbot_rag/app/api/deps.py:25` - cached service assembly.
  - Pattern:  `../chatbot_rag/app/api/routes/tourism.py:36` - tourism chat endpoint.
  - Pattern:  `../chatbot_rag/app/api/routes/tourism.py:49` - sanitized 500 error behavior.
  - API/Type: `../chatbot_rag/app/schemas/tourism.py:38` - `TourismChatResponse` contract.
  - API/Type: `../chatbot_rag/app/schemas/chat.py:17` - `ChatResponse` contract.
  - Test:     `../chatbot_rag/tests/test_tourism_api.py:30` - FastAPI TestClient endpoint pattern.
  - External: `https://fastapi.tiangolo.com/reference/apirouter/` - APIRouter semantics.
  - External: `https://fastapi.tiangolo.com/tutorial/static-files/` - static mount behavior.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_api_contract.py::test_project_template_health_regions_chat_contract`; run `pytest tests/test_project_template_api_contract.py::test_project_template_health_regions_chat_contract -q | tee .omo/evidence/task-4-api-red.txt` and confirm RED before backend parity is complete.
  - [ ] Sync backend files; run `pytest tests/test_project_template_api_contract.py::test_project_template_health_regions_chat_contract project_template/tests/test_tourism_api.py -q | tee .omo/evidence/task-4-api-green.txt`.
  - [ ] Run `cmp -s ../chatbot_rag/app/main.py project_template/app/main.py && cmp -s ../chatbot_rag/app/api/routes/tourism.py project_template/app/api/routes/tourism.py && echo backend-entrypoints-byte-match | tee .omo/evidence/task-4-backend-cmp.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: API endpoints respond through TestClient
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-4; tmux send-keys -t ulw-qa-task-4 'pytest tests/test_project_template_api_contract.py::test_project_template_health_regions_chat_contract -q; echo TASK4_DONE' C-m; sleep 3; tmux capture-pane -pt ulw-qa-task-4 -S -200 > .omo/evidence/task-4-api.txt; tmux kill-session -t ulw-qa-task-4
    Expected: .omo/evidence/task-4-api.txt contains TASK4_DONE and 1 passed.
    Evidence: .omo/evidence/task-4-api.txt

  Scenario: blank tourism chat does not leak internals
    Tool:     HTTP call
    Steps:    cd project_template && TOURISM_LIVE_LOOKUP_ENABLED=false python -m uvicorn app.main:app --host 127.0.0.1 --port 8764 > ../.omo/evidence/task-4-server.log 2>&1 & echo $! > ../.omo/evidence/task-4-server.pid; sleep 3; curl -i -sS -X POST http://127.0.0.1:8764/tourism/chat -H 'Content-Type: application/json' --data '{"message":"   "}' > ../.omo/evidence/task-4-blank-http.txt; kill $(cat ../.omo/evidence/task-4-server.pid); wait $(cat ../.omo/evidence/task-4-server.pid) 2>/dev/null || true
    Expected: .omo/evidence/task-4-blank-http.txt contains HTTP/1.1 400 and message는 비어 있을 수 없습니다, with no forbidden internal terms.
    Evidence: .omo/evidence/task-4-blank-http.txt
  ```

  Commit: YES | Message: `feat(api): 원본 FastAPI 라우터 계약을 맞춘다` | Files: [`project_template/app/**`, `project_template/tests/test_tourism_api.py`, `tests/test_project_template_api_contract.py`]

- [ ] 5. Nationwide data and query extraction parity

  What to do: Write failing tests for full nationwide region data and representative query extraction, then sync `data/processed/tour_area_codes.json`, `tourapi_bigdata_region_codes.json`, `admin_region_aliases.json`, and query-normalization support files. Ensure direct sigungu resolution and ambiguous aliases work.
  Must NOT do: Do not replace full nationwide data with samples; do not generate files from live APIs during this task; do not commit `data/generated/`.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [7, 9, 10, 11, 12] | Blocked by: [1, 2, 3]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `docs/original_first_tutorial_plan.md:176` - nationwide region requirements.
  - Pattern:  `../chatbot_rag/data/processed/tour_area_codes.json:3` - full `area_codes` root.
  - Pattern:  `../chatbot_rag/data/processed/tour_area_codes.json:325` - `강남구` mapping.
  - Pattern:  `../chatbot_rag/data/processed/tour_area_codes.json:901` - `해운대구` mapping.
  - Pattern:  `../chatbot_rag/data/processed/tour_area_codes.json:2839` - `제주시` mapping.
  - Pattern:  `../chatbot_rag/data/processed/tour_area_codes.json:2887` - ambiguous `중구` candidates.
  - Pattern:  `../chatbot_rag/app/services/tourism_query_service.py:16` - area constants and fallback.
  - Pattern:  `../chatbot_rag/app/services/tourism_query_service.py:298` - query extraction pipeline.
  - Pattern:  `../chatbot_rag/app/services/tourism_query_service.py:1138` - region index loading.
  - Test:     `../chatbot_rag/tests/test_tourism_quality_regression.py:17` - matrix builds from nationwide region index.
  - Test:     `../chatbot_rag/tests/test_tourism_query_service.py:42` - cache-backed extraction pattern.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_region_data.py::test_project_template_has_nationwide_region_index`; run `pytest tests/test_project_template_region_data.py::test_project_template_has_nationwide_region_index -q | tee .omo/evidence/task-5-region-red.txt` and confirm RED before data/query gaps are fixed.
  - [ ] Sync processed data/query support; run `pytest tests/test_project_template_region_data.py::test_project_template_has_nationwide_region_index project_template/tests/test_tourism_query_service.py::test_tourism_query_normalizes_noisy_region_and_condition project_template/tests/test_tourism_quality_regression.py::test_quality_region_extraction_matrix -q | tee .omo/evidence/task-5-region-green.txt`.
  - [ ] Run `cmp -s ../chatbot_rag/data/processed/tour_area_codes.json project_template/data/processed/tour_area_codes.json && echo region-data-byte-match | tee .omo/evidence/task-5-region-cmp.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: nationwide data summary is present
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-5; tmux send-keys -t ulw-qa-task-5 'cd project_template && jq "{area_count:(.area_codes|length), region_index_count:(.region_index|length), gangnam:.region_index[\"강남구\"], haeundae:.region_index[\"해운대구\"], jeju:.region_index[\"제주시\"], junggu:(.ambiguous_region_aliases[\"중구\"]|length)}" data/processed/tour_area_codes.json; echo TASK5_DONE' C-m; sleep 1; tmux capture-pane -pt ulw-qa-task-5 -S -200 > .omo/evidence/task-5-region-data.txt; tmux kill-session -t ulw-qa-task-5
    Expected: .omo/evidence/task-5-region-data.txt contains area_count 17, region_index_count >= 400, and junggu >= 3.
    Evidence: .omo/evidence/task-5-region-data.txt

  Scenario: query service resolves representative sigungu
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-5-query; tmux send-keys -t ulw-qa-task-5-query 'cd project_template && python - <<'"'"'PY'"'"'\nfrom app.services.tourism_query_service import TourismQueryService\nservice = TourismQueryService()\nfor message in [\"강남구 휠체어 관광지\", \"해운대구 유모차 관광지\", \"유성구 점자블록 관광지\", \"제주시 휠체어 관광지\"]:\n    query = service.extract(message)\n    print(message, query[\"area_name\"], query[\"sigungu_name\"], query[\"sigungu_code\"])\nPY\n echo TASK5_QUERY_DONE' C-m; sleep 2; tmux capture-pane -pt ulw-qa-task-5-query -S -220 > .omo/evidence/task-5-query.txt; tmux kill-session -t ulw-qa-task-5-query
    Expected: .omo/evidence/task-5-query.txt contains TASK5_QUERY_DONE and non-empty sigungu codes for all four messages.
    Evidence: .omo/evidence/task-5-query.txt
  ```

  Commit: YES | Message: `feat(data): 전국 관광 지역 인덱스를 이식한다` | Files: [`project_template/data/processed/**`, `project_template/app/services/tourism_query_service.py`, `project_template/app/services/korean_query_normalizer.py`, `tests/test_project_template_region_data.py`]

- [ ] 6. RAG services, repositories, prompts, and document scripts

  What to do: Write failing tests for normal RAG service behavior, retriever/vector-store interfaces, prompt loading, document ingestion shape, and document route stats/reindex. Then sync RAG-related app modules, prompts, repositories, utilities, and `scripts/ingest_all.py`/`scripts/rebuild_index.py`/`scripts/clear_vector_db.py` without shipping vector-store runtime files.
  Must NOT do: Do not create or commit Chroma runtime directories; do not call external LLM/Ollama in tests; use fakes for embeddings/vector store/LLM where source tests do.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [10, 11] | Blocked by: [1, 2, 3]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `docs/original_first_tutorial_plan.md:133` - required RAG stages.
  - Pattern:  `../chatbot_rag/app/services/rag_service.py:21` - answer pipeline.
  - Pattern:  `../chatbot_rag/app/api/routes/chat.py:10` - chat endpoint contract.
  - Pattern:  `../chatbot_rag/app/api/routes/documents.py:11` - document reindex contract.
  - Pattern:  `../chatbot_rag/app/core/config.py:25` - Chroma path configuration; path must point to runtime location but not ship runtime store.
  - Test:     `../chatbot_rag/tests/test_retriever.py:1` - retriever test pattern.
  - Test:     `../chatbot_rag/tests/test_prompt_builder.py:1` - prompt test pattern.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_rag_contract.py::test_rag_pipeline_uses_retrieved_context_and_sources`; run `pytest tests/test_project_template_rag_contract.py::test_rag_pipeline_uses_retrieved_context_and_sources -q | tee .omo/evidence/task-6-rag-red.txt` and confirm RED before RAG parity is fixed.
  - [ ] Sync RAG modules/prompts/scripts; run `pytest tests/test_project_template_rag_contract.py project_template/tests/test_retriever.py project_template/tests/test_prompt_builder.py project_template/tests/test_splitter.py -q | tee .omo/evidence/task-6-rag-green.txt`.
  - [ ] Run `test ! -e project_template/data/vector_store/chroma/chroma.sqlite3 && echo no-vector-runtime | tee .omo/evidence/task-6-no-vector-runtime.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: RAG service returns answer plus source with fakes
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-6; tmux send-keys -t ulw-qa-task-6 'pytest tests/test_project_template_rag_contract.py -q; echo TASK6_DONE' C-m; sleep 3; tmux capture-pane -pt ulw-qa-task-6 -S -200 > .omo/evidence/task-6-rag.txt; tmux kill-session -t ulw-qa-task-6
    Expected: .omo/evidence/task-6-rag.txt contains TASK6_DONE and all tests passed.
    Evidence: .omo/evidence/task-6-rag.txt

  Scenario: vector store runtime is absent after scripts sync
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-6-vector; tmux send-keys -t ulw-qa-task-6-vector 'cd project_template && find data/vector_store -type f ! -name ".gitkeep" -print; echo TASK6_VECTOR_DONE' C-m; sleep 1; tmux capture-pane -pt ulw-qa-task-6-vector -S -120 > .omo/evidence/task-6-vector.txt; tmux kill-session -t ulw-qa-task-6-vector
    Expected: .omo/evidence/task-6-vector.txt contains TASK6_VECTOR_DONE and no runtime file paths.
    Evidence: .omo/evidence/task-6-vector.txt
  ```

  Commit: YES | Message: `feat(rag): 원본 검색 생성 파이프라인을 맞춘다` | Files: [`project_template/app/services/{citation_service.py,document_loader.py,embedding_service.py,ingestion_service.py,llm_service.py,prompt_builder.py,rag_service.py,retriever.py,text_splitter.py,vector_store.py}`, `project_template/app/repositories/**`, `project_template/prompts/**`, `project_template/scripts/{ingest_all.py,rebuild_index.py,clear_vector_db.py}`, `project_template/tests/test_retriever.py`, `project_template/tests/test_prompt_builder.py`, `project_template/tests/test_splitter.py`, `tests/test_project_template_rag_contract.py`]

- [ ] 7. Tourism chat, TourAPI adapters, cache, and event logging

  What to do: Write failing tourism service tests for representative user flows, then sync `TourismChatService`, card codec, normalizer, condition/context/intent classifiers, TourAPI service/cache/usage, query event logger, and related tests. Preserve all diagnostic fields in API JSON while ensuring web visible text maps them to public labels.
  Must NOT do: Do not call real TourAPI in automated tests; do not require API keys; do not generate or commit SQLite response cache; do not change the public no-card/unsupported/clarification copy without tests.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [9, 10, 11, 12] | Blocked by: [1, 2, 3, 5]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `../chatbot_rag/app/services/tourism_chat_service.py:325` - top-level `answer` flow.
  - Pattern:  `../chatbot_rag/app/services/tourism_chat_service.py:347` - unsupported core clarification.
  - Pattern:  `../chatbot_rag/app/services/tourism_chat_service.py:376` - ambiguous region clarification.
  - Pattern:  `../chatbot_rag/app/services/tourism_chat_service.py:445` - live update start.
  - Pattern:  `../chatbot_rag/app/services/tourism_chat_service.py:474` - indexed retrieval fallback.
  - Pattern:  `../chatbot_rag/app/services/tourism_chat_service.py:488` - sample fallback.
  - Pattern:  `../chatbot_rag/app/services/tourism_chat_service.py:602` - session follow-up merging.
  - API/Type: `../chatbot_rag/app/schemas/tourism.py:16` - card schema.
  - API/Type: `../chatbot_rag/app/schemas/tourism.py:38` - response schema.
  - Test:     `../chatbot_rag/tests/test_tourism_chat_service.py:64` - indexed card/source smoke.
  - Test:     `../chatbot_rag/tests/test_tourism_chat_service.py:149` - live TourAPI fake pattern.
  - Test:     `../chatbot_rag/tests/test_tourism_query_event_logger.py:1` - event logger contract.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_tourism_contract.py::test_tourism_chat_cards_clarification_and_followup_contract`; run `pytest tests/test_project_template_tourism_contract.py::test_tourism_chat_cards_clarification_and_followup_contract -q | tee .omo/evidence/task-7-tourism-red.txt` and confirm RED before service parity is fixed.
  - [ ] Sync tourism modules/tests; run `pytest tests/test_project_template_tourism_contract.py project_template/tests/test_tourism_chat_service.py project_template/tests/test_tourism_query_service.py project_template/tests/test_tour_api_service.py project_template/tests/test_tourism_query_event_logger.py -q | tee .omo/evidence/task-7-tourism-green.txt`.
  - [ ] Run `find project_template/data/generated -type f ! -name ".gitkeep" -print | tee .omo/evidence/task-7-generated-files.txt` and confirm no generated cache/log files.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: tourism service handles cards and follow-up without live API
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-7; tmux send-keys -t ulw-qa-task-7 'cd project_template && TOURISM_LIVE_LOOKUP_ENABLED=false python - <<'"'"'PY'"'"'\nfrom app.core.config import Settings\nfrom app.services.tourism_chat_service import TourismChatService\nfrom app.services.tourism_query_service import TourismQueryService\nclass EmptyRetriever:\n    def retrieve(self, message):\n        return []\nsvc = TourismChatService(Settings(tourism_live_lookup_enabled=False, tourism_condition_transformer_enabled=False), EmptyRetriever(), TourismQueryService())\nfirst = svc.answer(\"서울에서 휠체어 관광지 추천\", session_id=\"qa-session\")\nsecond = svc.answer(\"시장 말고 실내 위주로\", session_id=\"qa-session\")\nprint(first.lookup_mode, len(first.cards), first.answer[:40])\nprint(second.lookup_mode, len(second.cards), second.answer[:40])\nPY\n echo TASK7_DONE' C-m; sleep 5; tmux capture-pane -pt ulw-qa-task-7 -S -260 > .omo/evidence/task-7-tourism.txt; tmux kill-session -t ulw-qa-task-7
    Expected: .omo/evidence/task-7-tourism.txt contains TASK7_DONE, no traceback, and two response lines with lookup modes.
    Evidence: .omo/evidence/task-7-tourism.txt

  Scenario: fake TourAPI path does not write runtime cache into template
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-7-cache; tmux send-keys -t ulw-qa-task-7-cache 'pytest project_template/tests/test_tourism_chat_service.py::test_tourism_chat_persists_live_tour_api_cards_to_markdown -q && find project_template/data/generated -type f ! -name ".gitkeep" -print; echo TASK7_CACHE_DONE' C-m; sleep 4; tmux capture-pane -pt ulw-qa-task-7-cache -S -220 > .omo/evidence/task-7-cache.txt; tmux kill-session -t ulw-qa-task-7-cache
    Expected: .omo/evidence/task-7-cache.txt contains TASK7_CACHE_DONE and no committed generated cache path.
    Evidence: .omo/evidence/task-7-cache.txt
  ```

  Commit: YES | Message: `feat(tourism): 관광 상담 흐름과 TourAPI 어댑터를 맞춘다` | Files: [`project_template/app/services/tour*.py`, `project_template/app/services/korean_*.py`, `project_template/app/schemas/tourism.py`, `project_template/tests/test_tourism_*.py`, `project_template/tests/test_tour_api_service.py`, `tests/test_project_template_tourism_contract.py`]

- [ ] 8. Static raw/eval corpus and utility scripts

  What to do: Write failing tests that prove static source data required by service/tests exists, then copy static `data/raw/tourism_accessible/`, `data/raw/example_faq.md`, `data/eval/*.jsonl`, non-generated processed training/eval fixtures, and selected utility scripts needed by tests. Use the manifest from Task 2 to exclude generated model artifacts, caches, logs, and local databases.
  Must NOT do: Do not copy `.venv`, `.pytest_cache`, `__pycache__`, vector stores, `data/generated/tour_api/`, data models, or source-local generated reports.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [10, 11] | Blocked by: [1, 2, 3]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `../chatbot_rag/tests/test_tourism_chat_service.py:15` - source tests read raw tourism markdown.
  - Pattern:  `../chatbot_rag/tests/test_tourism_quality_regression.py:17` - quality tests read processed region data.
  - Pattern:  `../chatbot_rag/scripts/audit_tourism_samples.py:1` - sample audit script needed by copied tests.
  - Pattern:  `../chatbot_rag/scripts/eval_tourism_chat.py:1` - eval script covered by copied tests.
  - Pattern:  `docs/original_first_tutorial_plan.md:236` - verification flow requires route, RAG, tourism, and web tests.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_static_corpus.py::test_template_static_corpus_supports_source_tests`; run `pytest tests/test_project_template_static_corpus.py::test_template_static_corpus_supports_source_tests -q | tee .omo/evidence/task-8-corpus-red.txt` and confirm RED before missing static corpus/scripts are fixed.
  - [ ] Sync static corpus/scripts; run `pytest tests/test_project_template_static_corpus.py project_template/tests/test_audit_tourism_samples.py project_template/tests/test_eval_tourism_chat_script.py project_template/tests/test_fetch_accessible_tourism_samples.py -q | tee .omo/evidence/task-8-corpus-green.txt`.
  - [ ] Run `find project_template/data -path '*/generated/*' -type f ! -name '.gitkeep' -print | tee .omo/evidence/task-8-generated-data-scan.txt` and confirm no generated run artifacts.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: raw tourism sample corpus supports card extraction tests
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-8; tmux send-keys -t ulw-qa-task-8 'cd project_template && test -f data/raw/tourism_accessible/seoul_sample_001.md && test -f data/raw/tourism_accessible/busan_sample_001.md && test -f data/eval/tourism_20_questions.jsonl && echo STATIC_CORPUS_PRESENT' C-m; sleep 1; tmux capture-pane -pt ulw-qa-task-8 -S -100 > .omo/evidence/task-8-corpus.txt; tmux kill-session -t ulw-qa-task-8
    Expected: .omo/evidence/task-8-corpus.txt contains STATIC_CORPUS_PRESENT.
    Evidence: .omo/evidence/task-8-corpus.txt

  Scenario: copied utility scripts are syntax-valid
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-8-scripts; tmux send-keys -t ulw-qa-task-8-scripts 'cd project_template && python -m py_compile scripts/audit_tourism_samples.py scripts/eval_tourism_chat.py scripts/fetch_accessible_tourism_samples.py; echo TASK8_SCRIPTS_DONE' C-m; sleep 2; tmux capture-pane -pt ulw-qa-task-8-scripts -S -120 > .omo/evidence/task-8-scripts.txt; tmux kill-session -t ulw-qa-task-8-scripts
    Expected: .omo/evidence/task-8-scripts.txt contains TASK8_SCRIPTS_DONE and no traceback.
    Evidence: .omo/evidence/task-8-scripts.txt
  ```

  Commit: YES | Message: `feat(data): 정적 관광 말뭉치와 평가 자료를 이식한다` | Files: [`project_template/data/raw/**`, `project_template/data/eval/**`, `project_template/data/processed/**`, `project_template/scripts/**`, `project_template/tests/test_audit_tourism_samples.py`, `project_template/tests/test_eval_tourism_chat_script.py`, `project_template/tests/test_fetch_accessible_tourism_samples.py`, `tests/test_project_template_static_corpus.py`]

- [ ] 9. Web UI and option-flow parity

  What to do: Write failing web-contract tests, then sync `frontend/web/index.html`, `app.js`, `styles.css`, `option_flow_builder.js`, and `frontend/web/README.md`. Preserve release/debug mode behavior, chat/option tabs, region select, suggestions, cards, sources, update notice, photo/help modal, and public mode labels.
  Must NOT do: Do not redesign the UI; do not remove diagnostic panel support from debug mode; do not show forbidden internal terms in visible release-mode text.

  Parallelization: Can parallel: NO | Wave 3 | Blocks: [10, 12] | Blocked by: [4, 5, 7]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `docs/original_first_tutorial_plan.md:148` - required web surface.
  - Pattern:  `../chatbot_rag/frontend/web/index.html:10` - app shell.
  - Pattern:  `../chatbot_rag/frontend/web/index.html:99` - composer.
  - Pattern:  `../chatbot_rag/frontend/web/index.html:147` - option builder.
  - Pattern:  `../chatbot_rag/frontend/web/index.html:254` - card template.
  - Pattern:  `../chatbot_rag/frontend/web/index.html:296` - help modal.
  - Pattern:  `../chatbot_rag/frontend/web/app.js:252` - `/tourism/chat` fetch.
  - Pattern:  `../chatbot_rag/frontend/web/app.js:327` - `/tourism/regions` fetch.
  - Pattern:  `../chatbot_rag/frontend/web/app.js:524` - response renderer.
  - Pattern:  `../chatbot_rag/frontend/web/app.js:587` - public mode labels.
  - Pattern:  `../chatbot_rag/frontend/web/option_flow_builder.js:34` - option message builder.
  - Test:     `../chatbot_rag/tests/test_tourism_option_flow_ui.py:28` - Node option-flow test pattern.
  - External: `https://playwright.dev/docs/screenshots` - screenshot artifact capture.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_web_contract.py::test_release_ui_has_original_controls_without_forbidden_visible_text`; run `pytest tests/test_project_template_web_contract.py::test_release_ui_has_original_controls_without_forbidden_visible_text -q | tee .omo/evidence/task-9-web-red.txt` and confirm RED before web parity is fixed.
  - [ ] Sync web files; run `pytest tests/test_project_template_web_contract.py project_template/tests/test_tourism_option_flow_ui.py -q | tee .omo/evidence/task-9-web-green.txt`.
  - [ ] Run `cmp -s ../chatbot_rag/frontend/web/index.html project_template/frontend/web/index.html && cmp -s ../chatbot_rag/frontend/web/app.js project_template/frontend/web/app.js && cmp -s ../chatbot_rag/frontend/web/option_flow_builder.js project_template/frontend/web/option_flow_builder.js && echo web-byte-match | tee .omo/evidence/task-9-web-cmp.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: option-flow builder creates natural Korean query
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-9; tmux send-keys -t ulw-qa-task-9 'cd project_template && node -e "const b=require(\"./frontend/web/option_flow_builder.js\"); console.log(b.buildOptionFlowMessage({area:\"서울\", sigungu:\"강남구\", conditions:[\"wheelchair\",\"restroom\"], intensity:\"required\", expansion:\"conditional\"}))"; echo TASK9_DONE' C-m; sleep 1; tmux capture-pane -pt ulw-qa-task-9 -S -120 > .omo/evidence/task-9-option-flow.txt; tmux kill-session -t ulw-qa-task-9
    Expected: .omo/evidence/task-9-option-flow.txt contains TASK9_DONE and 서울 강남구에서 휠체어 접근과 장애인 화장실 모두 있는 관광지 추천해줘.
    Evidence: .omo/evidence/task-9-option-flow.txt

  Scenario: release HTML visible text excludes forbidden terms
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-9-visible; tmux send-keys -t ulw-qa-task-9-visible 'pytest tests/test_project_template_web_contract.py::test_release_ui_has_original_controls_without_forbidden_visible_text -q; echo TASK9_VISIBLE_DONE' C-m; sleep 2; tmux capture-pane -pt ulw-qa-task-9-visible -S -160 > .omo/evidence/task-9-visible-text.txt; tmux kill-session -t ulw-qa-task-9-visible
    Expected: .omo/evidence/task-9-visible-text.txt contains TASK9_VISIBLE_DONE and test passed.
    Evidence: .omo/evidence/task-9-visible-text.txt
  ```

  Commit: YES | Message: `feat(web): 원본 관광 상담 화면을 맞춘다` | Files: [`project_template/frontend/web/**`, `project_template/tests/test_tourism_option_flow_ui.py`, `tests/test_project_template_web_contract.py`]

- [ ] 10. Migrated source test suite and root parity tests

  What to do: Write failing root-level parity tests for source-vs-template structure and copied test health, then finish migrating the source tests needed to prove backend, RAG, tourism, data, scripts, and UI contracts. Update tests only to account for template-relative paths and excluded runtime artifacts, not to weaken behavior.
  Must NOT do: Do not delete failing assertions to make the suite green; do not skip or xfail source parity tests; do not make tests depend on real API keys or external services.

  Parallelization: Can parallel: NO | Wave 3 | Blocks: [11, 12] | Blocked by: [4, 5, 6, 7, 8, 9]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `../chatbot_rag/tests/conftest.py:1` - source test import strategy.
  - Pattern:  `../chatbot_rag/tests/test_tourism_api.py:30` - route smoke tests.
  - Pattern:  `../chatbot_rag/tests/test_tourism_quality_regression.py:41` - high-volume region/condition matrices.
  - Pattern:  `../chatbot_rag/tests/test_tourism_chat_service.py:333` - live-update regression family.
  - Pattern:  `../chatbot_rag/tests/test_tourism_option_flow_ui.py:80` - UI contract test.
  - Pattern:  `tests/test_project_template_parity.py:46` - current root parity test to preserve/extend.
  - External: `https://fastapi.tiangolo.com/tutorial/testing/` - TestClient usage with pytest.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_full_parity.py::test_template_contains_required_source_test_surface`; run `pytest tests/test_project_template_full_parity.py::test_template_contains_required_source_test_surface -q | tee .omo/evidence/task-10-tests-red.txt` and confirm RED before test surface is complete.
  - [ ] Migrate/fix tests; run `pytest tests project_template/tests -q | tee .omo/evidence/task-10-tests-green.txt`.
  - [ ] Run `cd project_template && pytest tests -q | tee ../.omo/evidence/task-10-template-tests-green.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: root and template test suites pass
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-10; tmux send-keys -t ulw-qa-task-10 'pytest tests project_template/tests -q; echo TASK10_DONE' C-m; sleep 20; tmux capture-pane -pt ulw-qa-task-10 -S -400 > .omo/evidence/task-10-tests.txt; tmux kill-session -t ulw-qa-task-10
    Expected: .omo/evidence/task-10-tests.txt contains TASK10_DONE and no failures.
    Evidence: .omo/evidence/task-10-tests.txt

  Scenario: template tests pass from template root
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-10-template; tmux send-keys -t ulw-qa-task-10-template 'cd project_template && pytest tests -q; echo TASK10_TEMPLATE_DONE' C-m; sleep 20; tmux capture-pane -pt ulw-qa-task-10-template -S -400 > .omo/evidence/task-10-template-tests.txt; tmux kill-session -t ulw-qa-task-10-template
    Expected: .omo/evidence/task-10-template-tests.txt contains TASK10_TEMPLATE_DONE and no failures.
    Evidence: .omo/evidence/task-10-template-tests.txt
  ```

  Commit: YES | Message: `test(template): 원본 회귀 테스트 표면을 이식한다` | Files: [`project_template/tests/**`, `tests/test_project_template_*.py`, `project_template/conftest.py`]

- [ ] 11. Bounded API runtime QA harness

  What to do: Write failing API e2e tests/harness scripts that start `project_template` with live lookup disabled, exercise real HTTP endpoints, capture response artifacts, and cleanly kill the server. Then implement the minimal harness under `.omo/qa/` or `tests/helpers/` and use it for bounded QA evidence.
  Must NOT do: Do not leave uvicorn running; do not use real TourAPI secrets; do not use unbounded `sleep` loops; do not run tunnel scripts.

  Parallelization: Can parallel: NO | Wave 3 | Blocks: [12] | Blocked by: [4, 5, 6, 7, 8, 10]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `AGENTS.md:77` - hidden long-running server prohibition.
  - Pattern:  `../chatbot_rag/app/main.py:26` - expected endpoint registration.
  - Pattern:  `../chatbot_rag/run_tourism_debug_tunnel.sh:42` - source health check loop style; adapt only bounded local QA, not tunnel.
  - Pattern:  `../chatbot_rag/.env.example:53` - live lookup settings; disable for deterministic QA.
  - Test:     `tests/test_project_template_parity.py:46` - endpoint expectations.
  - External: `https://fastapi.tiangolo.com/tutorial/testing/` - API testing model.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_runtime_qa.py::test_bounded_server_harness_captures_http_contract`; run `pytest tests/test_project_template_runtime_qa.py::test_bounded_server_harness_captures_http_contract -q | tee .omo/evidence/task-11-api-red.txt` and confirm RED before harness exists/works.
  - [ ] Implement harness; run `pytest tests/test_project_template_runtime_qa.py::test_bounded_server_harness_captures_http_contract -q | tee .omo/evidence/task-11-api-green.txt`.
  - [ ] Run `lsof -iTCP:8765 -sTCP:LISTEN | tee .omo/evidence/task-11-port-after.txt || true` after QA and confirm no project_template uvicorn process remains.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: real HTTP endpoints return expected contracts
    Tool:     HTTP call
    Steps:    cd project_template && TOURISM_LIVE_LOOKUP_ENABLED=false TOURISM_QUERY_EVENT_LOG_ENABLED=false python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 > ../.omo/evidence/task-11-server.log 2>&1 & echo $! > ../.omo/evidence/task-11-server.pid; for i in $(seq 1 30); do curl -fsS http://127.0.0.1:8765/health >/dev/null && break; sleep 1; done; { curl -i -sS http://127.0.0.1:8765/health; printf "\n---REGIONS---\n"; curl -i -sS http://127.0.0.1:8765/tourism/regions; printf "\n---BLANK---\n"; curl -i -sS -X POST http://127.0.0.1:8765/tourism/chat -H 'Content-Type: application/json' --data '{"message":"   "}'; printf "\n---CHAT---\n"; curl -i -sS -X POST http://127.0.0.1:8765/tourism/chat -H 'Content-Type: application/json' --data '{"message":"서울에서 휠체어 관광지 추천","session_id":"qa-api"}'; } > ../.omo/evidence/task-11-api-http.txt; kill $(cat ../.omo/evidence/task-11-server.pid); wait $(cat ../.omo/evidence/task-11-server.pid) 2>/dev/null || true; lsof -iTCP:8765 -sTCP:LISTEN > ../.omo/evidence/task-11-cleanup.txt 2>&1 || true
    Expected: .omo/evidence/task-11-api-http.txt contains HTTP/1.1 200 for health/regions, HTTP/1.1 400 for blank chat, and a JSON tourism chat body; .omo/evidence/task-11-cleanup.txt has no listener.
    Evidence: .omo/evidence/task-11-api-http.txt

  Scenario: malformed JSON fails cleanly
    Tool:     HTTP call
    Steps:    cd project_template && TOURISM_LIVE_LOOKUP_ENABLED=false python -m uvicorn app.main:app --host 127.0.0.1 --port 8766 > ../.omo/evidence/task-11-error-server.log 2>&1 & echo $! > ../.omo/evidence/task-11-error-server.pid; for i in $(seq 1 30); do curl -fsS http://127.0.0.1:8766/health >/dev/null && break; sleep 1; done; curl -i -sS -X POST http://127.0.0.1:8766/tourism/chat -H 'Content-Type: application/json' --data '{"message":' > ../.omo/evidence/task-11-api-error.txt; kill $(cat ../.omo/evidence/task-11-error-server.pid); wait $(cat ../.omo/evidence/task-11-error-server.pid) 2>/dev/null || true
    Expected: .omo/evidence/task-11-api-error.txt contains HTTP/1.1 422 or 400 and no stack trace.
    Evidence: .omo/evidence/task-11-api-error.txt
  ```

  Commit: YES | Message: `test(runtime): bounded API QA 하네스를 추가한다` | Files: [`tests/test_project_template_runtime_qa.py`, `.omo/qa/**`]

- [ ] 12. Tutorial docs, README, and browser QA

  What to do: Write failing docs/browser contract tests, then update `project_template/README.md` and tutorial docs so a beginner can build the original-shaped app while the real app UI/API remain production-user-oriented. Add browser QA script/spec that starts the bounded server, opens `/tourism-ui/?mode=release`, verifies UI controls/cards/sources/no forbidden visible terms, submits a representative question, captures screenshot/action log, and cleans up.
  Must NOT do: Do not add tutorial copy to the app UI/API responses; do not reference missing source-only docs/images; do not include absolute local paths; do not leave browser/server processes open.

  Parallelization: Can parallel: NO | Wave 3 | Blocks: [] | Blocked by: [4, 5, 7, 9, 10, 11]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `docs/original_first_tutorial_plan.md:253` - tutorial documentation requirements.
  - Pattern:  `docs/original_first_tutorial_plan.md:260` - app screen must not become tutorial screen.
  - Pattern:  `AGENTS.md:81` - no machine-specific paths.
  - Pattern:  `project_template/README.md:1` - current README needs template-safe rewrite; it currently references source-only assets/docs and adjacent app repo.
  - Pattern:  `../chatbot_rag/frontend/web/index.html:296` - help modal content to preserve in UI, not tutorial prose.
  - Pattern:  `../chatbot_rag/frontend/web/app.js:524` - response renderer browser behavior.
  - External: `https://playwright.dev/docs/screenshots` - screenshot capture.
  - External: `https://playwright.dev/python/docs/library` - browser automation lifecycle.

  Acceptance criteria (agent-executable only):
  - [ ] Write `tests/test_project_template_docs.py::test_tutorial_docs_are_path_safe_and_do_not_pollute_ui`; run `pytest tests/test_project_template_docs.py::test_tutorial_docs_are_path_safe_and_do_not_pollute_ui -q | tee .omo/evidence/task-12-docs-red.txt` and confirm RED before docs/browser gaps are fixed.
  - [ ] Update docs/README and browser QA spec; run `pytest tests/test_project_template_docs.py tests/test_project_template_web_contract.py -q | tee .omo/evidence/task-12-docs-green.txt`.
  - [ ] Run real browser QA with Chrome: `npx playwright test .omo/qa/task-12-release-ui.spec.js --project=chromium | tee .omo/evidence/task-12-browser-green.txt`; if Chrome is not available, download and use `agent-browser` and write the exact fallback command plus output to `.omo/evidence/task-12-browser-fallback.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: release UI loads in real browser with no forbidden visible terms
    Tool:     playwright(real Chrome)
    Steps:    cd project_template && TOURISM_LIVE_LOOKUP_ENABLED=false TOURISM_QUERY_EVENT_LOG_ENABLED=false python -m uvicorn app.main:app --host 127.0.0.1 --port 8767 > ../.omo/evidence/task-12-server.log 2>&1 & echo $! > ../.omo/evidence/task-12-server.pid; for i in $(seq 1 30); do curl -fsS http://127.0.0.1:8767/health >/dev/null && break; sleep 1; done; cd .. && npx playwright test .omo/qa/task-12-release-ui.spec.js --project=chromium --reporter=line > .omo/evidence/task-12-release-ui.log 2>&1; kill $(cat .omo/evidence/task-12-server.pid); wait $(cat .omo/evidence/task-12-server.pid) 2>/dev/null || true; lsof -iTCP:8767 -sTCP:LISTEN > .omo/evidence/task-12-cleanup.txt 2>&1 || true
    Expected: .omo/evidence/task-12-release-ui.log reports passed, screenshot exists at .omo/evidence/task-12-release-ui.png, and cleanup file has no listener.
    Evidence: .omo/evidence/task-12-release-ui.png

  Scenario: docs are tutorial-only and path-safe
    Tool:     tmux
    Steps:    tmux new-session -d -s ulw-qa-task-12-docs; tmux send-keys -t ulw-qa-task-12-docs 'pytest tests/test_project_template_docs.py tests/test_project_template_hygiene.py::test_project_files_use_relative_paths -q; echo TASK12_DOCS_DONE' C-m; sleep 3; tmux capture-pane -pt ulw-qa-task-12-docs -S -220 > .omo/evidence/task-12-docs.txt; tmux kill-session -t ulw-qa-task-12-docs
    Expected: .omo/evidence/task-12-docs.txt contains TASK12_DOCS_DONE, tests passed, and no machine-specific path hits.
    Evidence: .omo/evidence/task-12-docs.txt
  ```

  Commit: YES | Message: `docs(template): 원본형 앱 제작 튜토리얼을 완성한다` | Files: [`project_template/README.md`, `docs/**`, `tests/test_project_template_docs.py`, `.omo/qa/task-12-release-ui.spec.js`, `.omo/evidence/.gitkeep`]

## Final verification wave (MANDATORY - after all implementation tasks)
> Runs in PARALLEL. ALL must APPROVE. Surface results to the caller and wait for an explicit "okay" before declaring complete.
- [ ] F1. Plan compliance audit - every task done, every acceptance criterion met
- [ ] F2. Code quality review - diagnostics clean, idioms match, no dead code
- [ ] F3. Real manual QA - every QA scenario executed with evidence captured
- [ ] F4. Scope fidelity - nothing extra shipped beyond Must-Have, nothing Must-NOT-Have introduced

Final wave exact commands:
- F1: `pytest tests project_template/tests -q | tee .omo/evidence/f1-all-tests.txt`
- F2: `python -m compileall -q project_template/app project_template/tests && bash -n project_template/run_tourism_debug_tunnel.sh project_template/run_tourism_release_tunnel.sh | tee .omo/evidence/f2-quality.txt`
- F3: `test -s .omo/evidence/task-11-api-http.txt && test -s .omo/evidence/task-12-release-ui.png && test -s .omo/evidence/task-1-hygiene.txt && echo evidence-present | tee .omo/evidence/f3-manual-qa.txt`
- F4: `find project_template -type f \( -name '*.pyc' -o -name '*.db' -o -name '*.sqlite3' -o -path '*/.pytest_cache/*' -o -path '*/__pycache__/*' \) -print | tee .omo/evidence/f4-scope-forbidden-files.txt` and `pytest tests/test_project_template_hygiene.py::test_project_files_use_relative_paths -q | tee .omo/evidence/f4-scope-paths.txt`

## Commit strategy
- One logical change per commit. Conventional Commits (`<type>(<scope>): <subject>` body + footer).
- Commit subjects must be Korean to follow `AGENTS.md:85`, while keeping the Conventional Commit prefix.
- Atomic: every commit builds and passes tests on its own.
- No "WIP" / "fix typo squash later" commits on the final branch - clean up before merge.
- Reference the plan file path in the final commit footer: `Plan: .omo/plans/original-app-parity-project-template.md`.

## Success criteria
- `project_template/` reproduces the original FastAPI/RAG/tourism/web/data/test surface from `../chatbot_rag` with runtime/generated artifacts excluded.
- All Must-Have shipped; all QA scenarios pass with captured evidence; F1-F4 approved; commit history clean.
- Root and template test suites pass from a clean checkout command path.
- Bounded HTTP and real-browser QA prove `/health`, `/tourism/regions`, `/tourism/chat`, and `/tourism-ui/?mode=release` work through real surfaces, with cleanup receipts.
- No machine-specific absolute paths, secrets, local DB/vector stores, `.venv`, cache files, logs, or generated run artifacts are included in project deliverables.
