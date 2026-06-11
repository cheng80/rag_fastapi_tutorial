# 관광 데이터 운영 문서

마지막 갱신: 2026-05-26

이 문서는 기존 데이터 수집 계획, 전국 시군구 fallback 규모 산정, 샘플 품질 QA 문서를 통합한 문서다. 관광 fallback 데이터 수집, TourAPI 호출량 관리, 전국 시군구 규모 산정, 샘플 품질 QA를 한 흐름에서 관리한다.

## 1. 운영 목표

2026-06-10 전까지 앱 구현보다 먼저 기본 관광 상담 서비스를 완성한다. live TourAPI 조회를 기본 응답 경로로 쓰되, API 장애/쿼터/네트워크 문제에 대비해 지역별 최소 fallback Markdown을 확보한다.

현재 상태:

| 항목 | 상태 |
|---|---|
| 광역 fallback 배치 | `mvp`, `fallback-1`, `fallback-2`, `fallback-3` 완료 |
| raw fallback Markdown | 904개 |
| Chroma 색인 | 905개 문서 / 914개 청크 |
| TourAPI 지역 코드 234개 중 3장 이상 확보 | 228개 시군구 |
| 현재 행정구역으로 안내할 TourAPI 과거 지명 | 청원군, 마산시, 진해시, 남제주군, 북제주군 |
| 공식 무장애 상세 3장 미만 지역 | 계룡시 1장 |

위 5개는 실제 fallback 부족 지역으로 표시하지 않는다. TourAPI 지역 코드 캐시에 남아 있는 과거 지명 입력을 현재 행정구역 기준으로 안내하기 위한 예외 매핑이다. 사용자 화면에는 내부 코드나 정규화라는 표현을 노출하지 않고, “현재는 ○○ 기준으로 안내드릴게요” 정도로만 말한다.

자동 예외 리포트는 아래 산출물로 갱신한다.

```bash
.venv/bin/python scripts/audit_tourism_samples.py
```

현재 로컬 산출물:

```text
data/generated/tour_api/tourism_sample_audit.md
data/generated/tour_api/sigungu_fallback_exception_report.md
data/generated/tour_api/sigungu_fallback_exception_report.json
```

2026-05-26 기준 예외 리포트 요약은 TourAPI 시군구 234개, 행안부 현행 매칭 228개, 과거 지명 예외 5개, 공식 무장애 상세 저커버리지 1개다.

| 예전 입력 | 현재 안내/조회 기준 |
|---|---|
| 청원군 | 청주시 |
| 마산시 | 창원시 |
| 진해시 | 창원시 진해구 안내, TourAPI 조회는 창원시 기준 |
| 남제주군 | 서귀포시 |
| 북제주군 | 제주시 |

계룡시는 실제 저커버리지 지역이다. 2026-05-17에 `--sigungu-fallback --areas 충청남도 --cards-per-sigungu 3 --rows 50`으로 재수집을 시도했지만, 무장애 전용 `areaBasedList2`가 `계룡문화예술의전당` 1건만 반환했다. 일반 관광 `searchKeyword2`는 계룡 관련 8건을 반환했으나, 7건은 `detailWithTour2` 무장애 상세가 비어 있어 접근성 근거 카드로 편입하지 않았다. 따라서 계룡시는 “수집 누락”이 아니라 “공식 무장애 상세 확인 후보 1건”으로 관리한다.

## 2. 수집 원칙

- 전국을 한 번에 수집하지 않는다.
- 한 실행은 1개 배치만 담당한다.
- 기본 실행은 `--rows 20`, `--max-api-calls 300` 안에서 끝낸다.
- 평시 fallback 수집 안전치는 엔드포인트별 500건 이하로 둔다.
- 예외적으로 1,000건 한도를 쓸 때도 429가 나오면 즉시 멈춘다.
- 수집 후에는 `scripts/audit_tourism_samples.py`, `scripts/rebuild_index.py`, `pytest`를 실행한다.
- API 일일 트래픽을 쓰는 작업이므로 같은 배치를 반복 실행하지 않는다.
- 외부 터널을 열어 둔 상태에서 live UI를 누르면 TourAPI 호출이 추가된다. 수집일에는 `uvicorn`과 `cloudflared` 종료 여부를 확인한다.

프로세스 확인:

```bash
ps -ef | rg 'fetch_accessible_tourism_samples|uvicorn|cloudflared' | rg -v rg
```

## 3. 수집 배치

| 배치 | 지역 | 목적 |
|---|---|---|
| MVP | 서울, 부산, 강릉 | 현재 데모와 회귀 테스트의 기준 데이터 |
| fallback-1 | 서울, 부산, 인천, 대전, 대구, 광주, 울산 | 동명이 시군구와 광역시 질문 방어 |
| fallback-2 | 경기, 강원, 제주, 경북, 경남 | 관광 수요가 큰 광역/도 단위 보강 |
| fallback-3 | 세종, 충북, 충남, 전북, 전남, 강릉 | 나머지 도 단위 fallback 보강 |

기본 실행 순서:

```bash
.venv/bin/python scripts/fetch_tour_area_codes.py
.venv/bin/python scripts/fetch_accessible_tourism_samples.py --preset mvp --rows 20 --max-api-calls 150
.venv/bin/python scripts/rebuild_index.py
.venv/bin/python -m pytest
```

추가 배치:

```bash
.venv/bin/python scripts/fetch_accessible_tourism_samples.py --preset fallback-1 --rows 20 --max-api-calls 300
.venv/bin/python scripts/rebuild_index.py
.venv/bin/python -m pytest

.venv/bin/python scripts/fetch_accessible_tourism_samples.py --preset fallback-2 --rows 20 --max-api-calls 300
.venv/bin/python scripts/rebuild_index.py
.venv/bin/python -m pytest

.venv/bin/python scripts/fetch_accessible_tourism_samples.py --preset fallback-3 --rows 20 --max-api-calls 300
.venv/bin/python scripts/rebuild_index.py
.venv/bin/python -m pytest
```

부족 지역만 좁혀 보강할 때:

```bash
.venv/bin/python scripts/fetch_accessible_tourism_samples.py --regions '부족한지역1,부족한지역2' --rows 10 --max-api-calls 100
.venv/bin/python scripts/rebuild_index.py
.venv/bin/python -m pytest -q
```

## 4. 호출량 기록

TourAPIService는 엔드포인트별 일일 1,000건 한도를 확인한 뒤 호출을 기록한다. 사용량 로그 기본 경로는 `data/generated/tour_api/usage/daily_usage.json`이다.

원본 TourAPI 응답은 기본적으로 `data/generated/tour_api/live_response_cache.sqlite3` SQLite 캐시에 저장한다. 캐시 대상은 `areaCode2`, `areaBasedList2`, `searchKeyword2`, `detailCommon2`, `detailWithTour2`이며, TTL은 지역 코드/상세 30일, 목록/검색 7일, 오류 1일이다. 캐시 적중은 실제 공공데이터 호출이 아니므로 일일 사용량에 기록하지 않는다. 저장 params와 cache key에는 `serviceKey`를 넣지 않는다.

캐시 요약/정리는 아래 스크립트로 한다.

```bash
.venv/bin/python scripts/manage_tour_api_response_cache.py
.venv/bin/python scripts/manage_tour_api_response_cache.py --clear --expired-only
.venv/bin/python scripts/manage_tour_api_response_cache.py --clear --operation areaBasedList2
```

당일 산출물을 기준으로 최소 사용량을 부트스트랩해야 하면:

```bash
.venv/bin/python scripts/bootstrap_tour_api_usage.py
```

2026-05-15 수집 로그와 live UI 스모크 기준 추정치:

| 엔드포인트 | 추정 호출 수 | 비고 |
|---|---:|---|
| `KorWithService2/areaBasedList2` | 약 21회 | 지역별 후보 목록 |
| `KorService2/detailCommon2` | 약 386회 | 후보 공통 상세 |
| `KorWithService2/detailWithTour2` | 약 385회 | 무장애 상세 |

2026-05-15에는 사용자의 명시 승인으로 엔드포인트별 500건 평시 안전치를 일시적으로 풀고 1,000건 기준까지 수집했다. 이후 `detailCommon2` 429 응답 후 즉시 중단했다. 같은 quota window에서는 추가 수집하지 않는다.

2026-05-16 이어받기 수집 및 서귀포시 보강 결과:

| 항목 | 결과 |
|---|---:|
| 추가 실행 `areaBasedList2` | 73회 |
| 추가 실행 `detailCommon2` | 167회 |
| 추가 실행 `detailWithTour2` | 167회 |
| 1차 Markdown 총량 | 808개 |
| 1차 감사 결과 | 파싱 실패 0, 중복 0, 필수 필드 누락 0 |
| 1차 Chroma 재색인 | 809개 문서 / 816개 청크 |
| 서귀포시 보강 후 Markdown 총량 | 904개 |
| 서귀포시 보강 후 Chroma 재색인 | 905개 문서 / 914개 청크 |
| 551건 live eval 후 사용량 | `areaBasedList2=93`, `detailCommon2=287`, `detailWithTour2=287` |

서귀포시 보강은 남제주군 통합 지명 질문과 서귀포시 실내/박물관/산책/가족 편의 질문의 저커버리지 문제를 줄이기 위해 수행했다.

## 5. 전국 시군구 규모 산정

전국 실사용 지역 제품 목표 상한은 250개 안팎으로 둔다. 현재 확정 기준은 TourAPI 캐시의 234개 시군구이며, 행안부 현행 시군구 alias 매칭은 228개다. 250개는 확정 행정구역 수가 아니라 행정시/일반구/생활권처럼 사용자가 지역명으로 물을 수 있는 제품 표현을 추가할 때의 상한이다.

`법정동 기준 시군구 단위.xlsx` 교차 확인 결과, 엑셀의 250행은 일반구를 별도 제품 표현으로 포함한 법정동 기준 목록이다. 일반구를 TourAPI 호출 단위인 시 단위로 접고, 군위군을 현행 대구 군위군으로 보정하면 229개가 되며, 이는 행안부 alias 228개에 세종특별자치시 1개를 더한 값과 맞는다. 따라서 fallback 수집과 호출량 산정은 계속 TourAPI 234개를 기준으로 하고, 제품 표현 목록은 별도 매핑 계층으로 관리한다.

시군구 하나를 수집할 때 대략 다음 호출이 필요하다.

```text
areaBasedList2 1회
detailCommon2 N회
detailWithTour2 N회
```

따라서 시군구별 `N`장 후보를 확인하면:

```text
총 호출 수 = 시군구 수 * (1 + 2N)
```

전국 총량:

| 시나리오 | 예상 Markdown | areaBasedList2 | detailCommon2 | detailWithTour2 | 전체 호출 |
|---|---:|---:|---:|---:|---:|
| TourAPI 234개 지역별 3장 | 702 | 234 | 702 | 702 | 1,638 |
| TourAPI 234개 지역별 5장 | 1,170 | 234 | 1,170 | 1,170 | 2,574 |
| TourAPI 234개 지역별 10장 | 2,340 | 234 | 2,340 | 2,340 | 4,914 |
| 제품 상한 250개 지역별 3장 | 750 | 250 | 750 | 750 | 1,750 |
| 제품 상한 250개 지역별 5장 | 1,250 | 250 | 1,250 | 1,250 | 2,750 |
| 제품 상한 250개 지역별 10장 | 2,500 | 250 | 2,500 | 2,500 | 5,250 |

권장 전략:

1. 지금은 904개 fallback과 228개 시군구 3장 이상 확보 상태를 유지한다.
2. 계룡시는 공식 무장애 상세 후보가 1건뿐이므로 억지로 일반 관광지를 fallback 카드에 넣지 않는다. 사용자에게는 확인된 1건을 보여주고, 더 필요하면 상위 지역으로 명시적으로 넓히는 질문을 제안한다.
3. 품질 QA에서 빈 지역이나 음식점/숙박 과다 지역이 드러나면 해당 지역만 보강한다.
4. 제품 상한 250개 대상 목록은 행정시/일반구/생활권 표현이 실제 질문에서 반복될 때만 별도로 확장한다.
5. 전국 시군구별 5장 이상은 하루에 끝내지 않고 quota window별로 분할한다.

## 6. 샘플 품질 QA

`data/raw/tourism_accessible/`는 live TourAPI 호출을 줄이고 시연 안정성을 확보하기 위한 fallback/색인 후보 데이터다. 추가 수집 전에 먼저 현재 샘플의 품질과 분포를 확인한다.

실행:

```bash
.venv/bin/python scripts/audit_tourism_samples.py
```

중복 콘텐츠ID를 실패 조건으로 보려면:

```bash
.venv/bin/python scripts/audit_tourism_samples.py --fail-on-duplicates
```

기본 리포트는 아래 위치에 생성된다.

```text
data/generated/tour_api/tourism_sample_audit.md
```

`data/generated/` 아래 산출물은 로컬 분석 결과이므로 커밋하지 않는다. 문서화가 필요한 결론만 이 문서 또는 `docs/project/progress_overview.md`에 반영한다.

확인 기준:

- Markdown 파일 수와 파싱 성공 수가 일치하는지 본다.
- 중복 `콘텐츠ID`가 많은지 확인한다.
- 주소, 출처 URL, 추천근거 같은 필수 카드 정보가 비어 있는지 확인한다.
- 지역별 파일 수가 MVP 테스트 지역과 주요 광역권을 충분히 덮는지 본다.
- 접근성 태그가 휠체어에만 치우치지 않고 주차, 화장실, 보조견, 유모차 등도 확인 가능한지 본다.
- 가족 태그가 부족하면 가족/유모차 질문의 답변 품질을 별도로 점검한다.

2026-05-15 감사 결과:

- Markdown 파일 808개 중 808개 파싱 성공
- 파싱 실패 0개
- 필수 필드 누락 0개
- 주소 확인 필요 0개
- 출처 URL 확인 필요 0개
- 중복 콘텐츠ID 0개

2026-05-16 서귀포시 보강 후에는 Markdown 총량이 904개가 됐고, Chroma는 905개 문서/914개 청크로 재색인했다.

2026-05-26 감사 결과:

- Markdown 파일 904개 중 904개 파싱 성공
- 파싱 실패 0개
- 중복 콘텐츠ID 0개
- 필수 필드 누락 0개
- 출처 URL 확인 필요 96개

중복 재발 방지:

- 수집 스크립트는 실행 시작 시 `data/raw/tourism_accessible/`와 `data/generated/tour_api/live_markdown/`의 기존 Markdown을 모두 읽어 콘텐츠ID 인덱스를 만든다.
- 이미 존재하는 콘텐츠ID는 상세 API 호출 전에 건너뛴다.
- 기존 샘플에 이미 중복 콘텐츠ID가 있으면 수집 시작 시 경고를 출력한다.
- 감사 스크립트는 `--fail-on-duplicates` 옵션으로 중복을 실패 조건으로 만들 수 있다.

접근성 태그 상위 항목:

- 대중교통 503개
- 휠체어 접근 477개
- 장애인 주차 402개
- 장애인 화장실 360개

가족 태그:

- 가족 친화 131개
- 영유아 동반 81개
- 수유실 71개
- 유모차 대여 61개
- 유아용 의자 52개

가족/유모차 질문은 휠체어 조건보다 근거가 적으므로 확장 eval에서 별도로 확인한다.

## 7. 다음 작업

1. 추가 수집 전 `scripts/audit_tourism_samples.py --fail-on-duplicates`를 먼저 실행한다.
2. 음식점/비관광 후보가 과하게 섞였는지 지역별로 샘플링한다.
3. 부족한 지역만 `--regions`로 좁혀 보강한다.
4. 보강 수집은 한 번에 `--max-api-calls 100` 이하로 시작한다.
5. 수집 후 `scripts/rebuild_index.py`와 `pytest`를 실행한다.
6. `lookup_mode=live/indexed/sample`별 응답 품질 QA와 확장 eval을 실행한다.

## 8. 일정 메모

| 기간 | 목표 |
|---|---|
| 5/15-5/18 | cache/fallback 우선 응답 경로와 fallback 배치 수집 안정화 |
| 5/19-5/24 | fallback-1, fallback-2 수집 및 지역/조건 QA |
| 5/25-5/31 | fallback-3 수집, eval, 오류/속도 보강 |
| 6/1-6/7 | 기본 서비스 고정, 웹 UI QA, 외부 터널 시연 검증 |
| 6/8-6/10 | 문서/데모 스크립트/최종 회귀 테스트 |

앱 또는 Flutter 구현은 이 일정 뒤로 둔다. 6월 10일 전에는 `/tourism/chat`, `/tourism-ui/`, Swagger, Cloudflare 터널로 기본 서비스 검증이 가능해야 한다.
