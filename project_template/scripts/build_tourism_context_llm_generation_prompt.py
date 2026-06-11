from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402


DEFAULT_TRAIN = PROJECT_ROOT / "data" / "processed" / "tourism_context_training.jsonl"
DEFAULT_HOLDOUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_hard_holdout.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_llm_prompts"


LABEL_DEFINITIONS = {
    "strict_and": "둘 다/모두/반드시/없으면 안 됨처럼 모든 조건을 필수로 묶는 요청",
    "soft_and": "여러 조건을 말하지만 일부 완화 가능한 요청. '있으면 좋고', '참고만', '가능하면'이 핵심",
    "or_condition": "A 또는 B, A가 없으면 B, 둘 중 하나면 충분한 요청",
    "add_condition": "이전 추천 결과에 새 조건을 추가하는 후속 발화",
    "replace_condition": "이전 조건을 취소/교체하고 새 조건으로 바꾸는 후속 발화",
    "exclude_condition": "특정 장소 유형/조건을 제외하거나 뒤로 보내는 후속 발화",
    "family_context": "아이/가족/영유아/아기 동반 맥락",
    "mobility_context": "휠체어/유모차/어르신/계단 회피/이동 부담 맥락",
    "specific_facility_required": "점자블록/주차/화장실/수어/자막/수유실 등 근거가 반드시 필요한 시설 조건",
}

SCENARIO_REQUIREMENTS = [
    "A와 B가 같이 등장하지만 strict AND가 아닌 문장",
    "A 또는 B가 strict AND로 오해되기 쉬운 문장",
    "A 말고 B에서 A는 버리고 B만 활성 조건인 문장",
    "추측하지 말고/짐작하지 말고처럼 '말고'가 exclude가 아닌 문장",
    "아이/가족 단어가 있지만 가족 여행이 아니라고 부정하는 문장",
    "유모차가 가족 편의인지 이동성인지 문맥으로 갈리는 문장",
    "점자/수어/주차/화장실이 시설 조건이 아니라 주제/분위기로 쓰인 문장",
    "이전 결과 유지 + 조건 추가와 이전 조건 교체가 헷갈리는 문장",
    "카페/식당/시장/숙박 제외와 새 선호 추가가 한 문장에 섞인 문장",
    "짧은 후속 발화지만 이전 맥락이 없으면 애매한 문장",
    "정중한 표현, 구어체, 오타에 가까운 띄어쓰기 변형",
    "아무 라벨도 없어야 하는 negative near-miss 문장",
]


def load_texts(path: Path) -> list[str]:
    if not path.exists():
        return []
    texts: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        text = str(payload.get("text") or "").strip()
        if text:
            texts.append(text)
    return texts


def sample_forbidden(train_path: Path, holdout_path: Path, limit: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    texts = list(dict.fromkeys(load_texts(train_path) + load_texts(holdout_path)))
    rng.shuffle(texts)
    return texts[:limit]


def build_prompt(args: argparse.Namespace) -> str:
    forbidden_examples = sample_forbidden(args.train, args.holdout, args.forbidden_examples, args.seed)
    labels = "\n".join(f"- `{label}`: {LABEL_DEFINITIONS[label]}" for label in CONTEXT_LABELS)
    scenarios = "\n".join(f"{index}. {scenario}" for index, scenario in enumerate(SCENARIO_REQUIREMENTS, start=1))
    forbidden = "\n".join(f"- {text}" for text in forbidden_examples)
    return f"""# 관광 문맥 해석 hard-style 학습셋 생성 요청

너는 한국어 관광 챗봇의 multi-label 문맥 해석 학습셋을 만드는 데이터 라벨러다.
목표는 쉬운 템플릿을 늘리는 것이 아니라, hard holdout에서 실패할 만한 문장을 학습셋에 추가하는 것이다.

## 생성 수량

- 정확히 {args.target_rows} rows를 JSONL로 생성한다.
- 한 줄에 JSON 객체 하나만 둔다.
- Markdown 표, 설명 문장, 코드펜스는 출력하지 않는다.

## 라벨 목록

{labels}

## 필수 생성 조건

{scenarios}

## 분포 조건

- `<none>`에 해당하는 labels `[]` row를 최소 10% 포함한다.
- multi-label row를 최소 45% 포함한다.
- `strict_and`와 `or_condition`은 같은 row에 동시에 붙이지 않는다.
- `replace_condition`은 버린 조건이 아니라 새로 활성화된 조건 기준으로 `specific_facility_required`, `family_context`, `mobility_context`를 붙인다.
- `soft_and`는 strict/add/replace/exclude/or와 함께 쓰지 않는다.
- `specific_facility_required`는 실제 시설 근거를 요구할 때만 붙인다. 시설 단어가 비유, 주제, 부정 맥락이면 붙이지 않는다.

## JSONL schema

필드는 반드시 아래만 쓴다.

```json
{{"id":"LLMCTX000001","text":"사용자 발화","labels":["soft_and"],"category":"soft_optional_facility","required_terms":[],"optional_terms":["유모차","산책"],"excluded_terms":[],"risk_tags":["soft-vs-strict"],"rationale":"짧은 라벨 근거"}}
```

## 금지 사항

- 아래 기존 문장을 그대로 쓰거나 조사/어미만 바꿔 쓰지 않는다.
- 템플릿처럼 같은 문장 구조를 반복하지 않는다.
- 한 category에 같은 표현을 몰아넣지 않는다.
- 라벨 정의가 애매하면 `rationale`에 왜 그렇게 봤는지 쓴다.

## 기존 문장 일부

{forbidden}

## 출력

JSONL만 출력한다.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a prompt for Codex/LLM hard-style tourism context data generation.")
    parser.add_argument("--target-rows", type=int, default=300)
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--batch-id", default="001")
    parser.add_argument("--forbidden-examples", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20260517)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prompt = build_prompt(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"context_llm_generation_prompt_{args.batch_id}.md"
    output.write_text(prompt, encoding="utf-8")
    print(json.dumps({"output": str(output.relative_to(PROJECT_ROOT)), "target_rows": args.target_rows}, ensure_ascii=False))


if __name__ == "__main__":
    main()
