from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api" / "keyword_variant_prompts"


CANONICAL_TERMS = {
    "휠체어": "휠체어 접근, 이동약자, 전동휠체어, 바퀴 의자처럼 이동 보조 맥락",
    "유모차": "유모차, 유아차, 아이 동반, 영유아 동반 맥락",
    "장애인 화장실": "장애인 화장실, 다목적 화장실, 접근 가능한 화장실",
    "장애인 주차": "장애인 주차, 가까운 주차, 주차 편의",
    "엘리베이터": "엘리베이터, 승강기, 층간 이동",
    "경사로": "경사로, 턱 없음, 계단 회피, 평탄한 접근로",
    "점자": "점자, 점자블록, 촉지도, 시각장애 안내",
    "수어": "수어, 수화, 자막, 문자안내, 청각장애 안내",
    "보조견": "보조견, 안내견 동반",
    "수유실": "수유실, 기저귀 교환대, 영유아 가족 편의",
}


def build_prompt(target_rows: int) -> str:
    term_lines = "\n".join(f"- `{term}`: {definition}" for term, definition in CANONICAL_TERMS.items())
    return f"""# 무장애 관광 핵심어 변형 학습데이터 생성 요청

너는 한국어 관광 챗봇의 핵심어/동의어/오타/띄어쓰기 변형 데이터를 만드는 데이터 생성자다.
목표는 사람이 하나씩 오타를 추가하지 않아도, 모델과 검증기가 어떤 표현이 어떤 조건으로 이어지는지 학습할 수 있게 하는 것이다.

## 생성 수량

- 정확히 {target_rows} rows를 JSONL로 생성한다.
- 한 줄에 JSON 객체 하나만 둔다.
- Markdown 표, 설명 문장, 코드펜스는 출력하지 않는다.

## canonical_term 목록

{term_lines}

## schema

필드는 반드시 아래만 사용한다.

```json
{{"id":"KWVAR000001","canonical_term":"휠체어","condition_label":"휠체어","variant":"휄체어","variant_type":"typo","user_query":"서울 강남구 근처에서 휄체어 관광지 추천해줘","expected_conditions":["휠체어"],"should_promote":true,"risk_tags":["typo","mobility"],"rationale":"휠체어의 흔한 모음 오타로 이동 접근성 조건이다"}}
```

## variant_type

- `typo`: 자모/모음/받침 오타
- `spacing`: 띄어쓰기 붕괴 또는 과잉 띄어쓰기
- `abbreviation`: 축약어, 줄임말, 구어체
- `synonym`: 의미상 동의어 또는 현장 표현
- `paraphrase`: 직접 핵심어 없이 상황으로 조건을 말함
- `negative`: 핵심어가 나오지만 조건으로 쓰면 안 되는 반례
- `ambiguous`: 추가 질문이 필요한 애매한 표현

## 필수 분포

- `typo`, `spacing`, `abbreviation`, `synonym`, `paraphrase`를 모두 포함한다.
- `negative`와 `ambiguous`를 합쳐 최소 15% 포함한다.
- 무띄어쓰기 문장을 최소 20% 포함한다.
- 실제 사용자가 문법을 틀리게 말한 짧은 문장을 최소 25% 포함한다.
- 지명과 핵심어가 붙은 문장을 충분히 포함한다. 예: `서울강남구휠쳐관광지`, `성남장애인화장실되는곳`.

## 라벨 원칙

- `condition_label`은 아래 중 하나만 사용한다.
  `휠체어`, `유모차`, `화장실`, `주차`, `엘리베이터`, `접근로`, `시각장애`, `청각장애`, `보조견`, `고령자`, `none`, `ambiguous`
- `expected_conditions`는 실제 추천 필터에 넣어야 하는 조건 목록이다.
- `negative`는 `condition_label`을 `none`, `expected_conditions`를 `[]`로 둔다.
- `ambiguous`는 사용자가 추가 설명을 해야 하므로 `condition_label`을 `ambiguous`로 둔다.
- `should_promote`는 런타임 사전 후보로 올려도 되는 표현이면 true, 위험하면 false다.

## 금지 사항

- 너무 깨끗한 문장만 만들지 않는다.
- 단순히 canonical term만 반복하지 않는다.
- 지명이나 시설명을 실제와 다르게 확정하지 않는다.
- 장애 표현을 비하적으로 만들지 않는다.
- 의료기관, 가격, 예약, 실시간 혼잡도처럼 현재 서비스 범위 밖 요구를 조건으로 만들지 않는다.

## 출력

JSONL만 출력한다.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a GPT prompt for tourism keyword variant training data generation.")
    parser.add_argument("--target-rows", type=int, default=1200)
    parser.add_argument("--batch-id", default="001")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"keyword_variant_generation_prompt_{args.batch_id}.md"
    output.write_text(build_prompt(args.target_rows), encoding="utf-8")
    print(json.dumps({"output": str(output.relative_to(PROJECT_ROOT)), "target_rows": args.target_rows}, ensure_ascii=False))


if __name__ == "__main__":
    main()
