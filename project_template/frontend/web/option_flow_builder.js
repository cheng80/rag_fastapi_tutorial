(function initOptionFlowBuilder(root) {
  const CONDITION_TEXT = {
    wheelchair: "휠체어 접근",
    route: "입구/동선 접근로",
    restroom: "장애인 화장실",
    parking: "장애인 주차",
    elevator: "엘리베이터",
    transit: "대중교통 접근",
    braille: "점자 안내",
    audio: "음성 안내",
    sign: "수어 안내",
    caption: "자막 안내",
    nursing: "수유실",
    changing: "기저귀 교환대",
    stroller: "유모차",
    senior: "어르신 이동 부담",
    guide_dog: "안내견 동반",
  };

  const PREFERENCE_TEXT = {
    indoor: "실내",
    quiet: "조용한",
    park: "공원이나 산책하기 좋은",
    museum: "박물관이나 전시",
  };

  const EXCLUSION_TEXT = {
    market: "시장은 제외",
    food: "음식점과 카페는 제외",
    lodging: "숙박은 제외",
    long_walk: "오래 걷는 코스는 제외",
  };

  function buildOptionFlowMessage(state) {
    const normalized = normalizeState(state);
    const regionText = [normalized.area, normalized.sigungu].filter(Boolean).join(" ").trim();
    const conditionTexts = normalized.conditions.map((key) => CONDITION_TEXT[key]).filter(Boolean);
    const preferenceTexts = normalized.preferences.map((key) => PREFERENCE_TEXT[key]).filter(Boolean);
    const exclusionTexts = normalized.exclusions.map((key) => EXCLUSION_TEXT[key]).filter(Boolean);
    const baseRegion = regionText || "선택한 지역";
    const chunks = [];

    let focusText = "";
    if (conditionTexts.length > 0) {
      focusText = conditionPhrase(conditionTexts, normalized.intensity);
    } else {
      focusText = "무장애";
    }

    if (preferenceTexts.length > 0) {
      focusText = `${preferenceTexts.join(", ")} ${focusText}`;
    }

    if (normalized.expansion === "local_only" && normalized.sigungu) {
      chunks.push(`${baseRegion} 안에서 ${focusText} 관광지 추천해줘`);
    } else {
      chunks.push(`${baseRegion}에서 ${focusText} 관광지 추천해줘`);
    }

    if (exclusionTexts.length > 0) {
      chunks.push(`${exclusionTexts.join(", ")}해줘`);
    }

    if (normalized.expansion === "conditional" && normalized.area && normalized.sigungu) {
      chunks.push(`부족하면 ${normalized.area} 전체로 넓혀줘`);
    }

    if (normalized.expansion === "area_now" && normalized.area) {
      chunks.push(`${normalized.area} 전체로 넓혀서 보여줘`);
    }

    return chunks.join(". ").replace(/\s+/g, " ").trim();
  }

  function normalizeState(state) {
    const value = state || {};
    return {
      area: String(value.area || "").trim(),
      sigungu: String(value.sigungu || "").trim(),
      conditions: uniqueStrings(value.conditions),
      preferences: uniqueStrings(value.preferences),
      exclusions: uniqueStrings(value.exclusions),
      intensity: value.intensity === "optional" ? "optional" : "required",
      expansion: ["conditional", "area_now", "local_only"].includes(value.expansion) ? value.expansion : "local_only",
    };
  }

  function uniqueStrings(values) {
    if (!Array.isArray(values)) return [];
    return [...new Set(values.map((value) => String(value || "").trim()).filter(Boolean))];
  }

  function conditionPhrase(conditionTexts, intensity) {
    const joined = joinKoreanList(conditionTexts);
    if (intensity === "optional") {
      return `${joined} 있으면 좋은`;
    }
    if (conditionTexts.length >= 2) {
      return `${joined} 모두 있는`;
    }
    return `${joined} 가능한`;
  }

  function joinKoreanList(items) {
    if (items.length <= 1) return items[0] || "";
    if (items.length === 2) return `${items[0]}${koreanAndParticle(items[0])} ${items[1]}`;
    return `${items.slice(0, -1).join(", ")}와 ${items.at(-1)}`;
  }

  function koreanAndParticle(text) {
    const last = String(text || "").trim().at(-1);
    if (!last) return "와";
    const code = last.charCodeAt(0);
    if (code < 0xac00 || code > 0xd7a3) return "와";
    return (code - 0xac00) % 28 === 0 ? "와" : "과";
  }

  const api = {
    buildOptionFlowMessage,
    optionFlowLabels: {
      conditions: CONDITION_TEXT,
      preferences: PREFERENCE_TEXT,
      exclusions: EXCLUSION_TEXT,
    },
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.OptionFlowBuilder = api;
})(typeof window !== "undefined" ? window : globalThis);
