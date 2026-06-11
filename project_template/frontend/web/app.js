const form = document.querySelector("#chatForm");
const messageInput = document.querySelector("#message");
const apiBaseInput = document.querySelector("#apiBase");
const submitButton = document.querySelector("#submitButton");
const requestState = document.querySelector("#requestState");
const diagnostics = document.querySelector("#diagnostics");
const answerText = document.querySelector("#answerText");
const answerToggleButton = document.querySelector("#answerToggleButton");
const clarificationBanner = document.querySelector("#clarificationBanner");
const clarificationTitle = document.querySelector("#clarificationTitle");
const clarificationDescription = document.querySelector("#clarificationDescription");
const suggestions = document.querySelector("#suggestions");
const sourceList = document.querySelector("#sourceList");
const cardsGrid = document.querySelector("#cards");
const cardCount = document.querySelector("#cardCount");
const clearButton = document.querySelector("#clearButton");
const cardTemplate = document.querySelector("#cardTemplate");
const demoMoreButton = document.querySelector("#demoMoreButton");
const swaggerLink = document.querySelector("#swaggerLink");
const redocLink = document.querySelector("#redocLink");
const openapiLink = document.querySelector("#openapiLink");
const helpButton = document.querySelector("#helpButton");
const helpModal = document.querySelector("#helpModal");
const closeHelpButton = document.querySelector("#closeHelpButton");
const photoModal = document.querySelector("#photoModal");
const photoModalImage = document.querySelector("#photoModalImage");
const photoModalTitle = document.querySelector("#photoModalTitle");
const photoModalAddress = document.querySelector("#photoModalAddress");
const photoModalMap = document.querySelector("#photoModalMap");
const photoModalSource = document.querySelector("#photoModalSource");
const closePhotoButton = document.querySelector("#closePhotoButton");
const debugToggleButton = document.querySelector("#debugToggleButton");
const debugPanel = document.querySelector("#debugPanel");
const chatScroll = document.querySelector("#chatScroll");
const userEcho = document.querySelector("#userEcho");
const typingIndicator = document.querySelector("#typingIndicator");
const toast = document.querySelector("#toast");
const updateNotice = document.querySelector("#updateNotice");
const updateNoticeTitle = document.querySelector("#updateNoticeTitle");
const updateNoticeDescription = document.querySelector("#updateNoticeDescription");
const updateNoticeAccept = document.querySelector("#updateNoticeAccept");
const updateNoticeDismiss = document.querySelector("#updateNoticeDismiss");
const promptDrawer = document.querySelector("#promptDrawer");
const optionDrawer = document.querySelector("#optionDrawer");
const chatModeButton = document.querySelector("#chatModeButton");
const optionModeButton = document.querySelector("#optionModeButton");
const optionArea = document.querySelector("#optionArea");
const optionSigungu = document.querySelector("#optionSigungu");
const optionIntensity = document.querySelector("#optionIntensity");
const optionExpansion = document.querySelector("#optionExpansion");
const optionSummary = document.querySelector("#optionSummary");
const debugMode = isLocalDebugMode();

const accessibilityLabels = {
  wheelchair: "휠체어",
  parking: "주차",
  restroom: "화장실",
  stroller: "유아차",
  nursing_room: "수유실",
  elevator: "엘리베이터",
  route: "동선",
};

let fullAnswerText = "";
let compactAnswerText = "";
let isAnswerExpanded = false;
let sessionId = createSessionId();
let lastSubmittedMessage = "";
let inputMode = "chat";
let chatDraftMessage = "";
let regionOptions = fallbackRegionOptions();
let optionGeneratedMessage = "";
let optionManualEdit = false;
let lastPhotoTrigger = null;
let nextSubmittedMessage = "";
let nextSubmittedDisplayMessage = "";
let liveUpdateController = null;
let pendingLiveUpdatePayload = null;
let requestGeneration = 0;

const demoPreview = {
  answer:
    "시연 예시입니다. 지역을 선택하거나 질문을 보내면 실제 /tourism/chat 응답으로 교체됩니다.\n\n서울 강남구 기준으로 휠체어 접근성, 주차, 화장실 확인이 필요한 관광지를 카드 형태로 보여줍니다.",
  cards: [
    {
      title: "서울 선릉과 정릉",
      address: "서울특별시 강남구 선릉로100길 1",
      recommendation_reason:
        "도심 접근성이 좋고 산책 동선이 비교적 단순해 보호자와 함께 이동 계획을 세우기 좋습니다.",
      accessibility_tags: ["휠체어 동선 확인", "주차 확인"],
      family_tags: ["가족 산책"],
      accessibility: {
        wheelchair: "일부 구간은 현장 경사와 노면 상태 확인 필요",
        parking: "방문 전 장애인 주차 가능 여부 확인 필요",
        restroom: "현장 안내 확인 필요",
      },
      source_name: "한국관광공사 무장애 여행 정보",
    },
    {
      title: "코엑스 아쿠아리움",
      address: "서울특별시 강남구 영동대로 513",
      recommendation_reason:
        "실내 이동 중심이라 날씨 영향을 줄일 수 있고, 가족 동반 시 관람 흐름을 설명하기 쉽습니다.",
      accessibility_tags: ["실내", "엘리베이터 확인"],
      family_tags: ["아이 동반"],
      accessibility: {
        elevator: "건물 내 승강 설비 동선 확인 필요",
        restroom: "편의시설 위치 확인 필요",
        route: "혼잡 시간대 우회 동선 확인 권장",
      },
      source_name: "한국관광공사 무장애 여행 정보",
    },
  ],
};

apiBaseInput.value = defaultApiBase();
syncApiDocLinks();
syncDebugVisibility();
syncPromptDrawerSummary();
apiBaseInput.addEventListener("input", syncApiDocLinks);
debugToggleButton.addEventListener("click", toggleDebugPanel);
helpButton.addEventListener("click", openHelp);
closeHelpButton.addEventListener("click", closeHelp);
closePhotoButton.addEventListener("click", closePhotoModal);
updateNoticeAccept.addEventListener("click", acceptPreparedLiveUpdate);
updateNoticeDismiss.addEventListener("click", hideUpdateNotice);
promptDrawer?.addEventListener("toggle", syncPromptDrawerSummary);
optionDrawer?.addEventListener("toggle", syncOptionDrawerSummary);
answerToggleButton.addEventListener("click", () => {
  setAnswerExpanded(!isAnswerExpanded);
});
helpModal.addEventListener("click", (event) => {
  if (event.target === helpModal) closeHelp();
});
photoModal.addEventListener("click", (event) => {
  if (event.target === photoModal) closePhotoModal();
});
renderDemoPreview();
initializeRegionOptions();
syncInputMode();
syncOptionFlowMessage({ silent: true });
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!photoModal.hidden) {
    closePhotoModal();
    return;
  }
  if (!helpModal.hidden) closeHelp();
});

chatModeButton?.addEventListener("click", () => setInputMode("chat"));
optionModeButton?.addEventListener("click", () => setInputMode("option"));
optionArea?.addEventListener("change", () => {
  populateSigunguOptions(optionArea.value);
  syncOptionFlowMessage();
});
optionSigungu?.addEventListener("change", syncOptionFlowMessage);
optionIntensity?.addEventListener("change", syncOptionFlowMessage);
optionExpansion?.addEventListener("change", syncOptionFlowMessage);
document.querySelectorAll("[data-option-condition], [data-option-preference], [data-option-exclusion]").forEach((control) => {
  control.addEventListener("change", syncOptionFlowMessage);
});
messageInput.addEventListener("input", () => {
  if (inputMode === "option") {
    optionManualEdit = messageInput.value.trim() !== optionGeneratedMessage.trim();
  }
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    setInputMode("chat");
    messageInput.value = button.dataset.prompt;
    closePromptDrawer();
    messageInput.focus();
    showToast("질문 예시를 입력했습니다.", "ok");
  });
});

document.querySelectorAll("[data-region]").forEach((button) => {
  button.addEventListener("click", () => {
    setInputMode("chat");
    document.querySelectorAll("[data-region]").forEach((regionButton) => {
      regionButton.setAttribute("aria-pressed", String(regionButton === button));
    });
    const condition = inferConditionText(messageInput.value);
    messageInput.value = `${button.dataset.region}에서 ${condition} 관광지 추천해줘`;
    closePromptDrawer();
    messageInput.focus();
    showToast(`${button.dataset.region} 기준으로 질문을 준비했습니다.`, "ok");
  });
});

clearButton.addEventListener("click", () => {
  requestGeneration += 1;
  cancelLiveUpdateWatch();
  hideUpdateNotice();
  document.querySelectorAll("[data-region]").forEach((regionButton) => {
    regionButton.setAttribute("aria-pressed", "false");
  });
  setState("대기 중");
  diagnostics.replaceChildren();
  renderClarificationBanner(null);
  suggestions.replaceChildren();
  suggestions.classList.remove("clarification-options", "condition-options", "region-options", "recovery-options", "expansion-options", "live-update-options");
  sessionId = createSessionId();
  chatDraftMessage = "";
  optionGeneratedMessage = "";
  optionManualEdit = false;
  resetOptionFlow();
  setInputMode("chat");
  userEcho.hidden = true;
  userEcho.textContent = "";
  typingIndicator.hidden = true;
  hideToast();
  sourceList.replaceChildren(createSourceEmpty());
  setAnswerText("질문을 보내면 답변과 추천 카드가 여기에 표시됩니다.", { empty: true });
  cardsGrid.replaceChildren();
  cardCount.textContent = "0개";
  demoMoreButton.disabled = true;
  demoMoreButton.hidden = true;
  demoMoreButton.textContent = "더 보기";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  requestGeneration += 1;
  const requestId = requestGeneration;
  cancelLiveUpdateWatch();
  hideUpdateNotice();
  const displayMessage = (nextSubmittedDisplayMessage || messageInput.value).trim();
  const message = (nextSubmittedMessage || messageInput.value).trim();
  nextSubmittedMessage = "";
  nextSubmittedDisplayMessage = "";

  if (!message || !displayMessage) {
    setState("입력 필요", "error");
    diagnostics.replaceChildren(createDiagnostic("질문을 입력해야 합니다."));
    showToast("질문을 입력해 주세요.", "error");
    messageInput.focus();
    return;
  }

  setLoading(true);
  collapseComposerAfterSubmit();
  lastSubmittedMessage = message;
  renderUserMessage(displayMessage);
  preparePendingResponse();
  suggestions.replaceChildren();
  renderClarificationBanner(null);
  suggestions.classList.remove("clarification-options", "condition-options", "region-options", "recovery-options", "expansion-options", "live-update-options");

  try {
    const response = await fetch(`${normalizedApiBase()}/tourism/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      renderError(response.status, payload);
      return;
    }

    if (requestId !== requestGeneration) return;
    renderResponse(payload || {});
  } catch (error) {
    setState("연결 실패", "error");
    showToast("서버에 연결하지 못했습니다.", "error");
    setAnswerText(`서버에 연결하지 못했습니다.\n${error.message}`);
    suggestions.replaceChildren();
    renderClarificationBanner(null);
    suggestions.classList.remove("clarification-options", "condition-options", "region-options", "recovery-options", "expansion-options", "live-update-options");
    sourceList.replaceChildren(createSourceEmpty("서버 연결 후 출처가 표시됩니다."));
    cardsGrid.replaceChildren();
    cardCount.textContent = "0개";
    demoMoreButton.disabled = true;
    demoMoreButton.hidden = true;
  } finally {
    if (requestId === requestGeneration) setLoading(false);
  }
});

function normalizedApiBase() {
  return apiBaseInput.value.replace(/\/+$/, "");
}

function syncApiDocLinks() {
  const base = normalizedApiBase() || defaultApiBase();
  swaggerLink.href = `${base}/docs`;
  redocLink.href = `${base}/redoc`;
  openapiLink.href = `${base}/openapi.json`;
}

function defaultApiBase() {
  const { protocol, hostname } = window.location;
  if (protocol === "file:") {
    return "http://127.0.0.1:8000";
  }
  if (["127.0.0.1", "localhost"].includes(hostname) && window.location.port === "5173") {
    return "http://127.0.0.1:8000";
  }
  return window.location.origin;
}

function isLocalDebugMode() {
  const params = new URLSearchParams(window.location.search);
  return params.get("mode") !== "release" && params.get("debug") !== "0";
}

function syncDebugVisibility() {
  document.body.classList.toggle("debug-mode", debugMode);
  document.body.classList.toggle("release-mode", !debugMode);
  debugPanel.hidden = !debugMode;
  debugToggleButton.setAttribute("aria-expanded", String(debugMode));
}

function collapseComposerAfterSubmit() {
  if (inputMode === "option" && optionDrawer) {
    optionDrawer.open = false;
    syncOptionDrawerSummary();
  }
  closePromptDrawer();
}

async function initializeRegionOptions() {
  renderAreaOptions();
  populateSigunguOptions(optionArea?.value || "");
  try {
    const response = await fetch(`${normalizedApiBase()}/tourism/regions`);
    if (!response.ok) return;
    const payload = await response.json();
    const fetched = normalizeRegionOptions(payload?.areas);
    if (fetched.length === 0) return;
    regionOptions = fetched;
    renderAreaOptions();
    populateSigunguOptions(optionArea?.value || "");
    syncOptionFlowMessage({ silent: true });
  } catch {
    populateSigunguOptions(optionArea?.value || "");
  }
}

function normalizeRegionOptions(areas) {
  if (!Array.isArray(areas)) return [];
  return areas
    .map((area) => ({
      name: String(area?.name || "").trim(),
      sigungu: Array.isArray(area?.sigungu)
        ? area.sigungu.map((name) => String(name || "").trim()).filter(Boolean)
        : [],
    }))
    .filter((area) => area.name);
}

function renderAreaOptions() {
  if (!optionArea) return;
  const selected = optionArea.value;
  optionArea.replaceChildren(createSelectOption("", "광역 지역 선택"));
  regionOptions.forEach((area) => {
    optionArea.append(createSelectOption(area.name, area.name));
  });
  optionArea.value = regionOptions.some((area) => area.name === selected) ? selected : "";
}

function populateSigunguOptions(areaName) {
  if (!optionSigungu) return;
  const area = regionOptions.find((candidate) => candidate.name === areaName);
  optionSigungu.replaceChildren();
  if (!area) {
    optionSigungu.append(createSelectOption("", "광역 지역을 먼저 선택"));
    optionSigungu.disabled = true;
    return;
  }
  optionSigungu.disabled = false;
  optionSigungu.append(createSelectOption("", "전체"));
  area.sigungu.forEach((sigungu) => {
    optionSigungu.append(createSelectOption(sigungu, sigungu));
  });
  optionSigungu.value = "";
}

function createSelectOption(value, label) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  return option;
}

function fallbackRegionOptions() {
  return [
    { name: "서울", sigungu: ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"] },
    { name: "부산", sigungu: ["강서구", "금정구", "기장군", "남구", "동구", "동래구", "부산진구", "북구", "사상구", "사하구", "서구", "수영구", "연제구", "영도구", "중구", "해운대구"] },
    { name: "인천", sigungu: ["강화군", "계양구", "미추홀구", "남동구", "동구", "부평구", "서구", "연수구", "옹진군", "중구"] },
    { name: "대전", sigungu: ["대덕구", "동구", "서구", "유성구", "중구"] },
    { name: "대구", sigungu: ["남구", "달서구", "달성군", "동구", "북구", "서구", "수성구", "중구", "군위군"] },
    { name: "광주", sigungu: ["광산구", "남구", "동구", "북구", "서구"] },
    { name: "울산", sigungu: ["중구", "남구", "동구", "북구", "울주군"] },
    { name: "세종", sigungu: ["세종특별자치시"] },
    { name: "제주", sigungu: ["제주시", "서귀포시", "북제주군", "남제주군"] },
  ];
}

function setInputMode(mode) {
  if (!["chat", "option"].includes(mode) || inputMode === mode) return;
  if (inputMode === "chat") {
    chatDraftMessage = messageInput.value;
  }
  inputMode = mode;
  syncInputMode();
  if (mode === "chat") {
    messageInput.value = chatDraftMessage;
    messageInput.focus();
    return;
  }
  syncOptionFlowMessage({ silent: true });
  optionArea?.focus();
}

function syncInputMode() {
  const isOption = inputMode === "option";
  promptDrawer.hidden = isOption;
  optionDrawer.hidden = !isOption;
  optionSummary.hidden = true;
  if (isOption) {
    closePromptDrawer();
    optionDrawer.open = true;
    syncOptionDrawerSummary();
  }
  chatModeButton?.setAttribute("aria-selected", String(!isOption));
  optionModeButton?.setAttribute("aria-selected", String(isOption));
  messageInput.readOnly = false;
  messageInput.classList.remove("generated-query");
  if (isOption) {
    submitButton.textContent = "선택 조건으로 찾기";
  } else if (!submitButton.disabled) {
    submitButton.textContent = "추천 받기";
  }
}

function syncOptionFlowMessage(options = {}) {
  if (!window.OptionFlowBuilder) return;
  const state = readOptionFlowState();
  const message = window.OptionFlowBuilder.buildOptionFlowMessage(state);
  const hasRegion = Boolean(state.area || state.sigungu);
  const hasSignal = hasRegion || state.conditions.length > 0 || state.preferences.length > 0 || state.exclusions.length > 0;
  const previousGeneratedMessage = optionGeneratedMessage;
  optionGeneratedMessage = hasSignal ? message : "";

  optionSummary.textContent = hasSignal ? message : "지역과 조건을 고르면 질문 문장으로 정리됩니다.";
  if (inputMode === "option" && (!optionManualEdit || !messageInput.value.trim() || messageInput.value.trim() === previousGeneratedMessage.trim())) {
    messageInput.value = hasSignal ? message : "";
    optionManualEdit = false;
  }
  if (!options.silent && hasSignal && inputMode === "option") {
    showToast("선택값을 질문 문장으로 정리했습니다.", "ok");
  }
}

function readOptionFlowState() {
  return {
    area: optionArea?.value || "",
    sigungu: optionSigungu?.value || "",
    conditions: checkedValues("[data-option-condition]"),
    preferences: checkedValues("[data-option-preference]"),
    exclusions: checkedValues("[data-option-exclusion]"),
    intensity: optionIntensity?.value || "required",
    expansion: optionExpansion?.value || "local_only",
  };
}

function checkedValues(selector) {
  return [...document.querySelectorAll(selector)]
    .filter((control) => control.checked)
    .map((control) => control.dataset.optionCondition || control.dataset.optionPreference || control.dataset.optionExclusion);
}

function resetOptionFlow() {
  if (optionArea) optionArea.value = "";
  populateSigunguOptions("");
  if (optionIntensity) optionIntensity.value = "required";
  if (optionExpansion) optionExpansion.value = "local_only";
  document.querySelectorAll("[data-option-condition], [data-option-preference], [data-option-exclusion]").forEach((control) => {
    control.checked = false;
  });
  syncOptionFlowMessage({ silent: true });
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.classList.toggle("is-loading", isLoading);
  submitButton.textContent = isLoading ? "찾는 중" : inputMode === "option" ? "선택 조건으로 찾기" : "추천 받기";
  typingIndicator.hidden = !isLoading;
  if (isLoading) {
    demoMoreButton.disabled = true;
    if (debugMode) {
      setState("질문 분석 중");
      diagnostics.replaceChildren(createDiagnostic("지역과 조건을 확인하고, 복합 질문이면 후보 순서를 한 번 더 점검합니다."));
    }
  }
}

function preparePendingResponse() {
  renderClarificationBanner(null);
  suggestions.replaceChildren();
  suggestions.classList.remove("clarification-options", "condition-options", "region-options", "recovery-options", "expansion-options", "live-update-options");
  sourceList.replaceChildren(createSourceEmpty("응답을 준비하는 중입니다."));
  setAnswerText("질문을 분석하고 추천 후보를 찾는 중입니다.", { empty: true });
  cardsGrid.replaceChildren();
  cardCount.textContent = "0개";
  demoMoreButton.disabled = true;
  demoMoreButton.hidden = true;
  demoMoreButton.textContent = "더 보기";
  scrollToResponseStart();
}

function setState(text, tone = "") {
  if (!debugMode) return;
  requestState.textContent = text;
  requestState.className = `state-pill ${tone}`.trim();
}

function renderResponse(payload, options = {}) {
  const cards = Array.isArray(payload.cards) ? payload.cards : [];
  const mode = payload.lookup_mode || "unknown";
  setState(modeLabel(mode, payload.degraded), modeTone(mode, payload.degraded));

  const notes = [modeDescription(mode)];
  if (payload.degraded) notes.push("일부 자료 확인이 원활하지 않아 준비된 자료로 먼저 안내했습니다.");
  if (payload.live_update_pending) notes.push("최신 추천 결과를 확인 중이며, 준비되면 상단 알림으로 반영할 수 있습니다.");
  if (payload.reasoning_assist_used) notes.push("복합 조건을 반영해 후보 순서를 조정했습니다.");
  if (Array.isArray(payload.reasoning_assist_notes)) {
    payload.reasoning_assist_notes.forEach((note) => notes.push(`확인 메모: ${note}`));
  }
  if (Array.isArray(payload.warnings)) notes.push(...payload.warnings);
  if (debugMode) {
    diagnostics.replaceChildren(...notes.map(createDiagnostic));
  }

  setAnswerText(payload.answer || "답변 문장이 비어 있습니다.", { empty: !payload.answer });
  const clarificationType = mode === "clarification" ? inferClarificationType(payload) : null;
  const suggestionType = clarificationType || inferSuggestionType(payload, cards);
  renderClarificationBanner(clarificationType);
  renderSuggestions(visibleSuggestedMessages(payload), suggestionType);
  renderSources(payload.sources || [], cards);
  cardCount.textContent = `${cards.length}개`;
  cardsGrid.replaceChildren(...cards.map((card) => renderCard(card, lastSubmittedMessage)));
  if (payload.live_update_pending) {
    showToast("새 추천 결과가 준비되면 알려드릴게요.", "ok");
    if (!options.skipLiveUpdateWatch) startLiveUpdateWatch();
  } else if (mode === "live_update") {
    showToast("새 추천 결과를 반영했습니다.", "ok");
  } else if (cards.length > 0) {
    showToast(`${cards.length}개의 추천 카드를 찾았습니다.`, "ok");
  }
  scrollToResponseStart();
}

function visibleSuggestedMessages(payload) {
  const messages = Array.isArray(payload?.suggested_messages) ? payload.suggested_messages : [];
  if (!payload?.live_update_pending) return messages;
  return messages.filter((message) => !/최신 결과 업데이트 보기|업데이트 보기/.test(message));
}

function renderDemoPreview() {
  if (debugMode) {
    setState("시연 예시");
    diagnostics.replaceChildren(createDiagnostic("지역 선택, 추천 카드, 더 보기, 출처, 경고 문구가 보이도록 구성한 초기 예시입니다."));
    setAnswerText(demoPreview.answer);
    sourceList.replaceChildren(
      createSourceEmpty("예시 출처: 한국관광공사 무장애 여행 정보"),
      createSourceEmpty("실제 응답 후 카드별 원문 링크가 표시됩니다."),
    );
    cardCount.textContent = `${demoPreview.cards.length}개`;
    cardsGrid.replaceChildren(...demoPreview.cards.map((card) => renderCard(card, "")));
  } else {
    setAnswerText("가고 싶은 지역과 동행 조건을 알려주세요. 추천 가능한 장소를 카드로 정리해 드립니다.", { empty: true });
    sourceList.replaceChildren(createSourceEmpty());
    cardCount.textContent = "0개";
    cardsGrid.replaceChildren();
  }
  demoMoreButton.disabled = true;
  demoMoreButton.hidden = true;
}

function modeLabel(mode, degraded) {
  if (mode === "live") return "최신 자료 응답";
  if (mode === "live_update") return "최신 결과 반영";
  if (mode === "live_update_pending") return "최신 결과 확인 중";
  if (mode === "live_update_timeout") return "확인 시간 초과";
  if (mode === "live_update_empty") return "새 결과 없음";
  if (mode === "live_top_up") return "최신 자료 보강";
  if (mode === "cache") return "저장 자료 응답";
  if (mode === "indexed") return degraded ? "준비 자료 응답" : "준비 자료 응답";
  if (mode === "sample") return "준비 자료 응답";
  if (mode === "clarification") return "추가 확인 필요";
  if (mode === "unsupported") return "지원 범위 밖";
  return degraded ? "확인 자료 응답" : "정상 응답";
}

function modeTone(mode, degraded) {
  if (mode === "clarification") return "warn";
  if (mode === "unsupported") return "warn";
  if (mode === "sample" || degraded) return "warn";
  if (mode === "cache" || mode === "live" || mode === "live_update" || mode === "live_update_pending" || mode === "live_top_up" || mode === "indexed") return "ok";
  return "";
}

function modeDescription(mode) {
  if (mode === "live") return "지역이 확정되어 최신 자료에서 접근성 정보를 확인했습니다.";
  if (mode === "live_update") return "추가로 확인한 최신 추천 결과를 반영했습니다.";
  if (mode === "live_update_pending") return "최신 추천 결과를 아직 확인 중입니다.";
  if (mode === "live_update_timeout") return "최신 추천 결과 확인 시간이 초과되어 먼저 안내한 결과를 유지했습니다.";
  if (mode === "live_update_empty") return "반영할 새 추천 결과가 없습니다.";
  if (mode === "live_top_up") return "저장된 후보에 최신 확인 결과를 보강했습니다.";
  if (mode === "cache") return "이전에 확인해 둔 같은 지역 관광지를 찾았습니다.";
  if (mode === "indexed") return "준비된 관광지 자료에서 조건에 맞는 카드를 찾았습니다.";
  if (mode === "sample") return "준비된 관광지 자료를 사용했습니다.";
  if (mode === "clarification") return "추천 전에 지역 또는 접근성 기준 확인이 필요합니다.";
  if (mode === "unsupported") return "현재 서비스에서 바로 확인하기 어려운 질문이라 관광지 카드를 만들지 않았습니다.";
  return "응답 상태를 확인하지 못했습니다.";
}

function renderError(status, payload) {
  setState(`오류 ${status}`, "error");
  const detail = payload?.detail;
  const message =
    typeof detail === "string"
      ? detail
      : detail?.message || "요청 처리 중 문제가 발생했습니다.";
  const code = typeof detail === "object" && detail?.code ? ` (${detail.code})` : "";

  setAnswerText(`${message}${code}`);
  showToast("요청 처리 중 문제가 발생했습니다.", "error");
  renderClarificationBanner(null);
  suggestions.replaceChildren();
  suggestions.classList.remove("clarification-options", "condition-options", "region-options");
  sourceList.replaceChildren(createSourceEmpty("오류가 해결되면 출처가 표시됩니다."));
  cardsGrid.replaceChildren();
  cardCount.textContent = "0개";
  demoMoreButton.disabled = true;
  demoMoreButton.hidden = true;
}

function renderClarificationBanner(type) {
  if (!type) {
    clarificationBanner.hidden = true;
    clarificationBanner.classList.remove("condition-clarification", "region-clarification", "live-update-banner");
    clarificationTitle.textContent = "추가 질문 필요";
    clarificationDescription.textContent = "아래 후보를 선택하면 원래 질문 맥락을 유지한 채 다시 조회합니다.";
    return;
  }

  const copy = {
    condition: {
      title: "조건 확인 필요",
      description: "의미가 겹치는 접근성 표현입니다. 원하는 기준을 선택하면 그 조건으로 다시 조회합니다.",
    },
    region: {
      title: "지역 선택 필요",
      description: "같은 이름의 지역이 여러 곳에 있습니다. 지역 후보를 선택하면 원래 질문 맥락을 유지해 다시 조회합니다.",
    },
    general: {
      title: "추가 질문 필요",
      description: "아래 후보를 선택하면 원래 질문 맥락을 유지한 채 다시 조회합니다.",
    },
    "live-update": {
      title: "새 추천 결과를 확인하고 있어요",
      description: "먼저 볼 수 있는 결과를 보여드렸습니다. 새 결과가 준비되면 상단 알림으로 바로 바꿔 볼 수 있습니다.",
    },
  }[type] || {
    title: "추가 질문 필요",
    description: "아래 후보를 선택하면 원래 질문 맥락을 유지한 채 다시 조회합니다.",
  };

  clarificationBanner.hidden = false;
  clarificationBanner.classList.toggle("condition-clarification", type === "condition");
  clarificationBanner.classList.toggle("region-clarification", type === "region");
  clarificationBanner.classList.toggle("live-update-banner", type === "live-update");
  clarificationTitle.textContent = copy.title;
  clarificationDescription.textContent = copy.description;
}

function inferClarificationType(payload) {
  const answer = String(payload?.answer || "");
  const messages = Array.isArray(payload?.suggested_messages) ? payload.suggested_messages : [];
  const joined = `${answer} ${messages.join(" ")}`;
  if (/접근성 의미|어르신 이동 부담|입구\/동선 접근로|휠체어 접근|대중교통 접근|장애인 화장실/.test(joined)) {
    return "condition";
  }
  if (/어느 지역|여러 시도|지역이 여러|서울 중구|부산 중구|인천 중구/.test(joined)) {
    return "region";
  }
  return "general";
}

function inferSuggestionType(payload, cards) {
  const messages = Array.isArray(payload?.suggested_messages) ? payload.suggested_messages : [];
  if ((payload?.lookup_mode === "unknown" || payload?.lookup_mode === "sample") && cards.length === 0 && messages.length > 0) {
    return "shortage";
  }
  if (messages.some((message) => /전체로 넓혀|범위.*넓혀/.test(message))) {
    return "expansion";
  }
  if (messages.some((message) => /최신 결과 업데이트 보기|업데이트 보기|최신 추천/.test(message))) {
    return "live-update";
  }
  return null;
}

function renderSuggestions(messages, suggestionType = null) {
  suggestions.replaceChildren();
  suggestions.classList.toggle("clarification-options", Boolean(suggestionType) && suggestionType !== "shortage" && messages.length > 0);
  suggestions.classList.toggle("condition-options", suggestionType === "condition" && messages.length > 0);
  suggestions.classList.toggle("region-options", suggestionType === "region" && messages.length > 0);
  suggestions.classList.toggle("recovery-options", suggestionType === "shortage" && messages.length > 0);
  suggestions.classList.toggle("expansion-options", suggestionType === "expansion" && messages.length > 0);
  suggestions.classList.toggle("live-update-options", suggestionType === "live-update" && messages.length > 0);
  const moreMessage = messages.find((message) => /더 보기|전부|20곳/.test(message));
  demoMoreButton.disabled = !moreMessage;
  demoMoreButton.hidden = !moreMessage;
  demoMoreButton.textContent = moreMessage || "더 보기";
  demoMoreButton.onclick = moreMessage
    ? () => {
      messageInput.value = moreMessage;
      showToast("추가 후보를 확인합니다.", "ok");
      form.requestSubmit();
    }
    : null;
  const seenLabels = new Set();
  messages.forEach((message) => {
    const button = document.createElement("button");
    button.type = "button";
    const label = suggestionButtonLabel(message, suggestionType);
    if (seenLabels.has(label)) return;
    seenLabels.add(label);
    button.textContent = label;
    if (label !== message) {
      button.title = message;
      button.setAttribute("aria-label", message);
    }
    button.addEventListener("click", () => {
      messageInput.value = label;
      nextSubmittedMessage = message;
      nextSubmittedDisplayMessage = label;
      showToast(
        suggestionType === "condition"
          ? "선택한 조건으로 다시 조회합니다."
          : suggestionType === "live-update"
            ? "준비된 새 추천 결과를 반영합니다."
            : "후속 질문을 보냅니다.",
        "ok",
      );
      form.requestSubmit();
    });
    suggestions.append(button);
  });
}

function suggestionButtonLabel(message, suggestionType) {
  if (suggestionType === "shortage") {
    if (/전체로 넓혀|범위|전체/.test(message)) return "같은 시·도까지 넓히기";
    if (/무장애 관광지/.test(message)) return "조건 완화하기";
    return "이 조건으로 다시 찾기";
  }
  if (suggestionType === "expansion" && /전체로 넓혀|범위.*넓혀/.test(message)) {
    return "같은 시·도까지 넓혀 보기";
  }
  if (/최신 결과 업데이트 보기|업데이트 보기/.test(message)) return "새 추천 결과 보기";
  if (/최신 정보 더 찾기|최신 추천 더 확인/.test(message)) return "최신 추천 더 확인하기";
  if (suggestionType !== "condition") return message;
  const patterns = [
    ["휠체어 접근", "휠체어 접근"],
    ["입구/동선 접근로", "입구/동선 접근로"],
    ["어르신 이동 부담 적은 곳", "어르신 이동 부담 적은 곳"],
    ["장애인 화장실", "장애인 화장실"],
    ["대중교통 접근", "대중교통 접근"],
  ];
  const matched = patterns.find(([needle]) => message.includes(needle));
  return matched ? matched[1] : message;
}

function setAnswerText(text, options = {}) {
  fullAnswerText = text;
  compactAnswerText = compactAnswer(text);
  isAnswerExpanded = false;
  answerText.classList.toggle("empty", Boolean(options.empty));
  answerText.textContent = compactAnswerText;
  syncAnswerToggle();
}

function setAnswerExpanded(expanded) {
  isAnswerExpanded = expanded;
  answerText.textContent = isAnswerExpanded ? fullAnswerText : compactAnswerText;
  syncAnswerToggle();
}

function compactAnswer(text) {
  const normalized = String(text || "").replace(/\n{3,}/g, "\n\n").trim();
  if (normalized.length <= 150) return normalized;

  const paragraphs = normalized.split(/\n{2,}/).filter(Boolean);
  const firstParagraph = paragraphs[0] || normalized;
  const sentences = firstParagraph
    .split(/(?<=[.!?。！？요다니다함됨세요])\s+/)
    .filter(Boolean);
  const summary = sentences.slice(0, 2).join(" ").trim();

  if (summary.length >= 48 && summary.length <= 180) return summary;
  return `${firstParagraph.slice(0, 150).trim()}...`;
}

function syncAnswerToggle() {
  const isCompactable = fullAnswerText.trim() !== compactAnswerText.trim();
  answerToggleButton.hidden = !isCompactable;
  answerToggleButton.textContent = isAnswerExpanded ? "접기" : "전체 보기";
  answerToggleButton.setAttribute("aria-expanded", String(isAnswerExpanded));
}

function renderSources(sources, cards) {
  sourceList.replaceChildren();
  const seen = new Set();
  const sourceItems = [];

  sources.forEach((source) => {
    const title = source.title || source.source || source.name || "검색 문서";
    const url = source.url || source.source_url;
    const key = `${title}:${url || ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    sourceItems.push({ title, url });
  });

  cards.forEach((card) => {
    const title = publicSourceName(card.source_name || "한국관광공사 무장애 여행 정보");
    const url = usableSourceUrl(card.source_url);
    const key = `${title}:${url || ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    sourceItems.push({ title, url });
  });

  if (sourceItems.length === 0) {
    sourceList.append(createSourceEmpty("출처 정보가 비어 있습니다. 카드별 출처를 확인하세요."));
    return;
  }

  sourceItems.slice(0, 6).forEach((source) => {
    const item = document.createElement(source.url ? "a" : "span");
    item.className = "source-item";
    item.textContent = source.title;
    if (source.url) {
      item.href = source.url;
      item.target = "_blank";
      item.rel = "noreferrer";
    }
    sourceList.append(item);
  });
}

function inferConditionText(message) {
  if (message.includes("유아차") || message.includes("아이") || message.includes("가족")) {
    return "유아차 가족";
  }
  if (message.includes("고령자") || message.includes("어르신") || message.includes("노인")) {
    return "휠체어 고령자";
  }
  if (message.includes("휠체어") || message.includes("장애인")) {
    return "휠체어";
  }
  return "무장애";
}

function closePromptDrawer() {
  if (promptDrawer) promptDrawer.open = false;
}

function syncPromptDrawerSummary() {
  const summary = promptDrawer?.querySelector("summary");
  if (summary) {
    summary.setAttribute("aria-label", `지역·예시 선택 ${promptDrawer.open ? "접기" : "열기"}`);
    const chevron = summary.querySelector(".drawer-chevron");
    if (chevron) chevron.textContent = "";
  }
}

function syncOptionDrawerSummary() {
  const summary = optionDrawer?.querySelector("summary");
  if (summary) {
    summary.setAttribute("aria-label", `선택 조건 ${optionDrawer.open ? "접기" : "열기"}`);
    const chevron = summary.querySelector(".drawer-chevron");
    if (chevron) chevron.textContent = "";
  }
}

function renderCard(card, queryText = "") {
  const node = cardTemplate.content.firstElementChild.cloneNode(true);
  const media = node.querySelector(".card-media");
  const title = node.querySelector("h3");
  const address = node.querySelector(".address");
  const reason = node.querySelector(".reason");
  const evidenceHighlights = node.querySelector(".evidence-highlights");
  const details = node.querySelector(".details");
  const sourceChip = node.querySelector(".source-chip");

  title.textContent = card.title || "이름 없는 장소";
  address.textContent = card.address || "주소 확인 필요";
  reason.textContent = card.recommendation_reason || "추천 사유 확인 필요";
  sourceChip.textContent = card.source_name ? "출처 있음" : "출처 확인";

  if (card.image_url) {
    const mediaButton = document.createElement("button");
    mediaButton.type = "button";
    mediaButton.className = "card-media-button";
    mediaButton.setAttribute("aria-label", `${card.title || "장소"} 사진 크게 보기`);

    const image = document.createElement("img");
    image.src = card.image_url;
    image.alt = `${card.title || "장소"} 사진`;
    image.loading = "lazy";
    image.decoding = "async";

    const zoomLabel = document.createElement("span");
    zoomLabel.className = "media-zoom-label";
    zoomLabel.textContent = "사진 크게 보기";

    mediaButton.append(image, zoomLabel);
    mediaButton.addEventListener("click", () => openPhotoModal(card, mediaButton));
    media.replaceChildren(mediaButton);
  } else {
    media.setAttribute("aria-hidden", "true");
  }

  const evidenceItems = cardEvidenceHighlights(card, queryText);
  evidenceHighlights.replaceChildren(...evidenceItems.map(([label, value]) => createEvidenceChip(label, value)));
  evidenceHighlights.hidden = evidenceItems.length === 0;

  if (card.tel) {
    details.append(createDetail("전화", card.tel));
  }

  const sourceUrl = usableSourceUrl(card.source_url);
  if (sourceUrl) {
    const source = document.createElement("a");
    source.href = sourceUrl;
    source.target = "_blank";
    source.rel = "noreferrer";
    source.textContent = "원문 보기";
    details.append(createDetail("출처", source));
  } else {
    details.append(createDetail("출처", publicSourceName(card.source_name || "한국관광공사 무장애 여행 정보")));
  }

  const rawDetailRows = rawDetailEntries(card);
  if (rawDetailRows.length > 0) {
    const detailPanel = document.createElement("div");
    detailPanel.className = "raw-detail-panel";
    detailPanel.hidden = true;

    const rawList = document.createElement("dl");
    rawList.className = "raw-details";
    rawDetailRows.forEach(([label, value]) => {
      const row = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = label;
      dd.textContent = normalizeDisplayText(value);
      row.append(dt, dd);
      rawList.append(row);
    });
    detailPanel.append(rawList);

    const actions = document.createElement("div");
    actions.className = "card-actions";

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = "상세 정보";
    toggle.addEventListener("click", () => {
      detailPanel.hidden = !detailPanel.hidden;
      toggle.textContent = detailPanel.hidden ? "상세 정보" : "상세 접기";
      toggle.setAttribute("aria-expanded", String(!detailPanel.hidden));
    });
    toggle.setAttribute("aria-expanded", "false");
    actions.append(toggle);

    const mapUrl = mapSearchUrl(card);
    if (mapUrl) {
      const mapLink = document.createElement("a");
      mapLink.href = mapUrl;
      mapLink.target = "_blank";
      mapLink.rel = "noreferrer";
      mapLink.textContent = "지도 검색";
      actions.append(mapLink);
    }

    node.querySelector(".card-body").append(actions, detailPanel);
  }

  return node;
}

function openPhotoModal(card, trigger) {
  const title = card.title || "이름 없는 장소";
  lastPhotoTrigger = trigger;
  photoModalTitle.textContent = title;
  photoModalAddress.textContent = card.address || "주소 확인 필요";
  photoModalImage.src = card.image_url;
  photoModalImage.alt = `${title} 사진`;

  const mapUrl = mapSearchUrl(card);
  photoModalMap.hidden = !mapUrl;
  if (mapUrl) {
    photoModalMap.href = mapUrl;
  }

  const sourceUrl = usableSourceUrl(card.source_url);
  photoModalSource.hidden = !sourceUrl;
  if (sourceUrl) {
    photoModalSource.href = sourceUrl;
  }

  photoModal.hidden = false;
  document.body.classList.add("modal-open");
  closePhotoButton.focus();
}

function closePhotoModal() {
  photoModal.hidden = true;
  photoModalImage.removeAttribute("src");
  document.body.classList.remove("modal-open");
  lastPhotoTrigger?.focus();
  lastPhotoTrigger = null;
}

function cardEvidenceHighlights(card, queryText = "") {
  const raw = normalizeObject(card.raw_fields);
  const accessibility = normalizeObject(card.accessibility);
  const candidates = [
    ["휠체어", wheelchairEvidence(accessibility, raw)],
    ["동선", routeEvidence(accessibility, raw)],
    ["화장실", firstValue(accessibility.restroom, raw["화장실"])],
    ["주차", parkingEvidence(accessibility, raw)],
    ["승강", firstValue(accessibility.elevator, raw["엘리베이터"])],
    ["수어/자막", firstValue(raw["수어안내"], raw["자막/영상안내"], raw["청각장애"], raw["안내시설"])],
    ["점자/촉지", firstValue(raw["점자블록"], raw["점자홍보물"], raw["안내시스템"], raw["시각장애 기타"])],
    ["유아", firstValue(accessibility.stroller, accessibility.nursing_room, raw["유모차"], raw["수유실"], raw["유아용 의자"])],
    ["대중교통", raw["대중교통"]],
    ["보조견", raw["보조견"]],
  ];
  const primaryFacts = dedupeEvidenceCandidates(candidates);
  const summarizedEvidenceTexts = primaryFacts.map(([, value]) => normalizeForEvidenceCompare(value));
  const accessibilityFacts = Object.entries(accessibility)
    .filter(([key, value]) => shouldShowEvidenceForFocus(key, queryText) && value)
    .map(([key, value]) => [accessibilityLabels[key] || key, value])
    .filter(([, value]) => {
      const normalized = normalizeForEvidenceCompare(value);
      return normalized && !summarizedEvidenceTexts.some((text) => evidenceTextsOverlap(text, normalized));
    });
  const conditionFacts = conditionTagEvidence(card, [...primaryFacts, ...accessibilityFacts]);

  return dedupeEvidenceCandidates([...primaryFacts, ...accessibilityFacts, ...conditionFacts])
    .filter(([, value]) => Boolean(value))
    .sort(([labelA], [labelB]) => evidencePriority(labelA, queryText) - evidencePriority(labelB, queryText))
    .slice(0, 6)
    .map(([label, value]) => [label, normalizeDisplayText(value)]);
}

function shouldShowEvidenceForFocus(key, queryText) {
  const focus = inferQueryConditionFocus(queryText);
  if (!focus) return true;
  if (focus === "visual" || focus === "hearing") return false;
  if (focus === "family") return ["stroller", "nursing_room", "route", "elevator"].includes(key);
  if (focus === "wheelchair") return ["wheelchair", "route", "elevator", "restroom", "parking"].includes(key);
  return true;
}

function wheelchairEvidence(accessibility, raw) {
  const rental = firstValue(accessibility.wheelchair, raw["휠체어"]);
  if (rental && /대여/.test(rental)) return rental;
  return firstValue(rental, raw["출입통로"]);
}

function routeEvidence(accessibility, raw) {
  const routeLikeValue = [raw["접근로"], raw["출입통로"], accessibility.route, raw["대중교통"]].find(
    (value) => value && routeLike(value) && !parkingDominant(value),
  );
  return routeLikeValue || (accessibility.route && !parkingDominant(accessibility.route) ? accessibility.route : null);
}

function parkingEvidence(accessibility, raw) {
  return [raw["주차"], accessibility.parking].find((value) => value && parkingLike(value));
}

function routeLike(value) {
  return /(출입|접근|경사|턱|문턱|평지|통로|동선|정류장|버스|지하철|대중교통)/.test(String(value || ""));
}

function parkingLike(value) {
  return /(주차|주차장|주차구역|주차 대수|전용 주차)/.test(String(value || ""));
}

function parkingDominant(value) {
  const text = String(value || "");
  return parkingLike(text) && !/(출입구까지|통로|동선|경사|턱|문턱|평지|대중교통|버스|정류장)/.test(text);
}

function dedupeEvidenceCandidates(candidates) {
  const result = [];
  const seen = [];
  candidates.forEach(([label, value]) => {
    const normalized = normalizeForEvidenceCompare(value);
    if (!normalized) return;
    if (seen.some((previous) => evidenceTextsOverlap(previous, normalized))) return;
    result.push([label, value]);
    seen.push(normalized);
  });
  return result;
}

function normalizeForEvidenceCompare(value) {
  return normalizeDisplayText(value)
    .replace(/[_·,./()]/g, " ")
    .replace(/\s+/g, "")
    .trim();
}

function evidenceTextsOverlap(left, right) {
  if (!left || !right) return false;
  if (left === right) return true;
  const shorter = left.length <= right.length ? left : right;
  const longer = left.length > right.length ? left : right;
  if (shorter.length >= 12 && longer.includes(shorter)) return true;
  if (sharedEvidenceSignals(left, right) >= 2) return true;
  const leftTokens = evidenceTokens(left);
  const rightTokens = evidenceTokens(right);
  if (leftTokens.length === 0 || rightTokens.length === 0) return false;
  const shared = leftTokens.filter((token) => rightTokens.includes(token));
  return shared.length >= 3 && shared.length / Math.min(leftTokens.length, rightTokens.length) >= 0.6;
}

function sharedEvidenceSignals(left, right) {
  const signals = [
    "턱이없어",
    "문턱없이",
    "휠체어접근",
    "휠체어통과",
    "경사로",
    "장애인전용주차",
    "주차구역",
    "장애인화장실",
    "엘리베이터",
    "점자",
    "수어",
    "자막",
    "유모차",
    "수유실",
  ];
  return signals.filter((signal) => left.includes(signal) && right.includes(signal)).length;
}

function evidenceTokens(text) {
  return text
    .split(/(?=주출입구|출입구|휠체어|경사로|문턱|턱|장애인|주차|화장실|엘리베이터|점자|수유|유모차|대중교통|버스|정류장)/)
    .map((token) => token.trim())
    .filter((token) => token.length >= 2);
}

function evidencePriority(label, queryText) {
  const focus = inferQueryConditionFocus(queryText);
  if (focus === "visual") {
    if (label === "점자/촉지") return 0;
    if (label === "수어/자막") return 5;
  }
  if (focus === "hearing") {
    if (label === "수어/자막") return 0;
    if (label === "점자/촉지") return 5;
  }
  if (focus === "family" && label === "유아") return 0;
  if (focus === "wheelchair" && ["휠체어", "동선", "승강", "화장실", "주차"].includes(label)) return 0;
  const defaultOrder = ["휠체어", "동선", "화장실", "주차", "승강", "대중교통", "점자/촉지", "수어/자막", "보조견", "유아"];
  const index = defaultOrder.indexOf(label);
  return index >= 0 ? index + 10 : 40;
}

function conditionTagEvidence(card, existingFacts) {
  const existingLabels = new Set(existingFacts.map(([label]) => label));
  return [...(card.accessibility_tags || []), ...(card.family_tags || [])]
    .filter(Boolean)
    .map((tag) => [conditionLabelFromTag(tag), normalizeDisplayText(tag)])
    .filter(([label]) => label && !existingLabels.has(label))
    .map(([label, tag]) => [label, fallbackEvidenceText(label, tag)]);
}

function conditionLabelFromTag(tag) {
  const text = String(tag || "");
  if (/(휠체어|접근|무장애)/.test(text)) return "휠체어";
  if (/(동선|경사|통로|턱|접근로)/.test(text)) return "동선";
  if (/(화장실)/.test(text)) return "화장실";
  if (/(주차)/.test(text)) return "주차";
  if (/(엘리베이터|승강)/.test(text)) return "승강";
  if (/(대중교통|버스|지하철)/.test(text)) return "대중교통";
  if (/(점자|촉지|시각|오디오|음성)/.test(text)) return "점자/촉지";
  if (/(수어|수화|자막|청각|문자)/.test(text)) return "수어/자막";
  if (/(보조견|안내견)/.test(text)) return "보조견";
  if (/(유아|영유아|가족|수유|유모차|유아차|기저귀)/.test(text)) return "유아";
  return text.length <= 8 ? text : "";
}

function fallbackEvidenceText(label, tag) {
  const suffix = "상세 위치와 이용 가능 여부는 방문 전 확인해 주세요.";
  if (label === tag) return suffix;
  return `${tag} 기준에 맞는 후보입니다. ${suffix}`;
}

function inferQueryConditionFocus(queryText) {
  const text = String(queryText || "").replace(/\s+/g, "");
  if (/(점자|점자블록|촉지|오디오가이드|음성안내|시각장애)/.test(text)) return "visual";
  if (/(수어|수화|자막|문자안내|청각장애)/.test(text)) return "hearing";
  if (/(유모차|유아차|수유실|기저귀|아이|가족)/.test(text)) return "family";
  if (/(휠체어|휄체어|휠채어|접근성좋|접근좋)/.test(text)) return "wheelchair";
  return "";
}

function normalizeObject(value) {
  return value && typeof value === "object" ? value : {};
}

function firstValue(...values) {
  return values.find((value) => typeof value === "string" && value.trim());
}

function rawDetailEntries(card) {
  const rows = [];
  const seen = new Set();
  const labels = {
    parking: "주차",
    route: "접근로",
    publictransport: "대중교통",
    ticketoffice: "매표소",
    promotion: "홍보물",
    wheelchair: "휠체어",
    exit: "출입통로",
    elevator: "엘리베이터",
    restroom: "화장실",
    auditorium: "관람석",
    room: "객실",
    handicapetc: "장애인 기타",
    braileblock: "점자블록",
    helpdog: "보조견",
    guidehuman: "안내요원",
    audioguide: "오디오가이드",
    bigprint: "큰활자",
    brailepromotion: "점자홍보물",
    guidesystem: "안내시스템",
    blindhandicapetc: "시각장애 기타",
    signguide: "수어안내",
    videoguide: "자막/영상안내",
    hearingroom: "청각장애 객실",
    hearinghandicapetc: "청각장애 기타",
    stroller: "유모차",
    lactationroom: "수유실",
    babysparechair: "유아용 의자",
    infantsfamilyetc: "영유아 기타",
  };

  Object.entries(card.raw_fields || {}).forEach(([key, value]) => {
    if (!value) return;
    const label = labels[key] || key;
    rows.push([label, normalizeDisplayText(value)]);
    seen.add(label);
  });

  Object.entries(card.accessibility || {}).forEach(([key, value]) => {
    const label = accessibilityLabels[key] || key;
    if (!value || seen.has(label)) return;
    rows.push([label, normalizeDisplayText(value)]);
  });

  return rows;
}

function mapSearchUrl(card) {
  const query = [card.title, card.address].filter(Boolean).join(" ");
  if (!query) return null;
  return `https://map.naver.com/p/search/${encodeURIComponent(query)}`;
}

function usableSourceUrl(url) {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.hostname === "access.visitkorea.or.kr" && parsed.pathname.startsWith("/detail/")) {
      return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}

function publicSourceName(sourceName) {
  return String(sourceName || "").replace(" OpenAPI", "");
}

function normalizeDisplayText(value) {
  return String(value || "")
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function createEvidenceChip(label, value) {
  const chip = document.createElement("div");
  chip.className = "evidence-item";

  const name = document.createElement("strong");
  name.textContent = label;

  const text = document.createElement("span");
  text.textContent = value;

  chip.append(name, text);
  return chip;
}

function createDetail(label, value) {
  const row = document.createElement("div");
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = label;
  if (value instanceof Node) {
    dd.append(value);
  } else {
    dd.textContent = normalizeDisplayText(value);
  }
  row.append(dt, dd);
  return row;
}

function createDiagnostic(text) {
  const note = document.createElement("span");
  note.className = "diagnostic";
  note.textContent = text;
  return note;
}

function createSourceEmpty(text = "응답 후 한국관광공사 자료와 카드별 출처가 표시됩니다.") {
  const empty = document.createElement("span");
  empty.className = "source-empty";
  empty.textContent = text;
  return empty;
}

function toggleDebugPanel() {
  if (!debugMode) return;
  debugPanel.hidden = !debugPanel.hidden;
  debugToggleButton.setAttribute("aria-expanded", String(!debugPanel.hidden));
}

function renderUserMessage(message) {
  userEcho.textContent = message;
  userEcho.hidden = false;
}

function showToast(message, tone = "") {
  toast.textContent = message;
  toast.className = `toast ${tone}`.trim();
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(hideToast, 2600);
}

function hideToast() {
  window.clearTimeout(showToast.timer);
  toast.hidden = true;
  toast.textContent = "";
  toast.className = "toast";
}

function cancelLiveUpdateWatch() {
  if (liveUpdateController) {
    liveUpdateController.abort();
    liveUpdateController = null;
  }
  pendingLiveUpdatePayload = null;
}

async function startLiveUpdateWatch() {
  cancelLiveUpdateWatch();
  const controller = new AbortController();
  liveUpdateController = controller;
  const watchGeneration = requestGeneration;

  try {
    const response = await fetch(`${normalizedApiBase()}/tourism/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "최신 결과 업데이트 보기", session_id: sessionId }),
      signal: controller.signal,
    });
    const payload = await response.json().catch(() => null);
    if (controller.signal.aborted || watchGeneration !== requestGeneration || liveUpdateController !== controller) return;
    liveUpdateController = null;
    if (!response.ok || !payload) return;
    if (payload.lookup_mode === "live_update") {
      pendingLiveUpdatePayload = payload;
      showUpdateNotice();
      showToast("새 추천 결과가 준비됐습니다.", "ok");
    } else if (payload.lookup_mode === "live_update_timeout") {
      showToast("확인이 길어져 먼저 안내한 결과를 유지합니다.", "ok");
    }
  } catch (error) {
    if (error.name !== "AbortError") {
      liveUpdateController = null;
    }
  }
}

function showUpdateNotice() {
  updateNoticeTitle.textContent = "새 추천 결과가 준비됐어요";
  updateNoticeDescription.textContent = "방금 확인한 결과로 추천 카드를 바꿔 볼까요?";
  updateNotice.hidden = false;
}

function hideUpdateNotice() {
  updateNotice.hidden = true;
}

function acceptPreparedLiveUpdate() {
  const payload = pendingLiveUpdatePayload;
  if (!payload) {
    hideUpdateNotice();
    return;
  }
  pendingLiveUpdatePayload = null;
  hideUpdateNotice();
  renderResponse(payload, { skipLiveUpdateWatch: true });
}

function scrollToResponseStart() {
  window.requestAnimationFrame(() => {
    const target = userEcho.hidden ? document.querySelector(".answer-panel") : userEcho;
    const offset = target.offsetTop - chatScroll.offsetTop - 12;
    chatScroll.scrollTop = Math.max(0, offset);
  });
}

function createSessionId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function openHelp() {
  helpModal.hidden = false;
  document.body.classList.add("modal-open");
  closeHelpButton.focus();
}

function closeHelp() {
  helpModal.hidden = true;
  document.body.classList.remove("modal-open");
  helpButton.focus();
}
