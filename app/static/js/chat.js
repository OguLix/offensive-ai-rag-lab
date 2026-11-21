"use strict";

const EMPTY_ANSWER = {
  title: "Belum ada jawaban",
  body: "Klik tombol + di sebelah kiri kotak pesan untuk mengatur serangan, mitigasi, atau koleksi, lalu kirim pertanyaan.",
};

const LOADING_ANSWER = {
  title: "Menunggu jawaban dari model",
  body: "Generasi di CPU bisa lambat. Tombol kirim nonaktif sampai jawaban datang.",
  action: { label: "Menunggu jawaban", disabled: true },
};

const ERROR_COPY = {
  400: {
    meta: "Error: permintaan tidak valid",
    title: "Permintaan tidak valid",
    detail: "Periksa pertanyaan, koleksi, dan toggle mitigasi.",
  },
  501: {
    meta: "Error: pipeline belum siap",
    title: "Pipeline RAG belum siap",
    detail: "Backend masih stub. Coba lagi setelah Fase 1 selesai.",
  },
  503: {
    meta: "Error: Ollama mati",
    title: "Ollama tidak dapat dijangkau",
    detail: "Pastikan Ollama berjalan di localhost, lalu kirim ulang.",
  },
  500: {
    meta: "Error: galat server",
    title: "Terjadi galat di server",
    detail: "Coba lagi. Jika tetap gagal, periksa log Flask.",
  },
};

const MITIGATION_GROUPS = [
  {
    id: "M1",
    label: "M1 Prompt dan filter",
    flags: ["prompt_hardening", "input_filter", "output_filter"],
  },
  {
    id: "M2",
    label: "M2 Konteks dokumen",
    flags: ["context_isolation", "retrieval_sanitizer"],
  },
  {
    id: "M3",
    label: "M3 Asal dokumen (saat ingest)",
    note: "M3 berjalan saat ingest. Untuk melihat efeknya, bandingkan koleksi kb_poisoned dan kb_poisoned_sanitized di menu Method.",
    flags: ["ingest_sanitizer", "provenance_check"],
  },
];

const state = {
  options: null,
  busy: false,
  sessions: [],
  activeSessionId: null,
  nextSessionNum: 1,
  lastQuestion: "",
  lastPromptJson: "",
  activeTab: "chunks",
  dockOpen: false,
  activeFlyout: "collections",
  currentAnswerState: "empty",
  currentAnswerView: EMPTY_ANSWER,
};

const els = {
  modelName: document.getElementById("model-name"),
  historyList: document.getElementById("history-list"),
  summaryCollection: document.getElementById("summary-collection"),
  summaryMitigations: document.getElementById("summary-mitigations"),
  disableMitigations: document.getElementById("disable-mitigations"),
  resetChat: document.getElementById("reset-chat"),
  conversationHeading: document.getElementById("conversation-heading"),
  assistantLabel: document.querySelector("#active-assistant-group .assistant-label"),
  thread: document.getElementById("thread"),
  pastTurns: document.getElementById("past-turns"),
  questionBubble: document.getElementById("question-bubble"),
  questionText: document.getElementById("question-text"),
  answerPanel: document.getElementById("answer-panel"),
  answerMeta: document.getElementById("answer-meta"),
  answerCard: document.getElementById("answer-card"),
  answerTitle: document.getElementById("answer-title"),
  answerBody: document.getElementById("answer-body"),
  answerStatus: document.getElementById("answer-status"),
  answerProgress: document.getElementById("answer-progress"),
  answerAction: document.getElementById("answer-action"),
  dockToggle: document.getElementById("dock-toggle"),
  chatControls: document.getElementById("chat-controls"),
  attackMenu: document.getElementById("attack-menu"),
  attackPanel: document.getElementById("attack-panel"),
  mitigationMenu: document.getElementById("mitigation-menu"),
  mitigationPanel: document.getElementById("mitigation-panel"),
  mitigationGroups: document.getElementById("mitigation-groups"),
  methodMenu: document.getElementById("method-menu"),
  collections: document.getElementById("collections"),
  form: document.getElementById("chat-form"),
  question: document.getElementById("question"),
  send: document.getElementById("send"),
  tabChunks: document.getElementById("tab-chunks"),
  tabPrompt: document.getElementById("tab-prompt"),
  chunks: document.getElementById("chunks"),
  promptView: document.getElementById("prompt-view"),
  messages: document.getElementById("messages"),
  copyPrompt: document.getElementById("copy-prompt"),
  chunkCount: document.getElementById("chunk-count"),
  mobileNavButtons: document.querySelectorAll(".mobile-nav-btn"),
  panels: document.querySelectorAll("[data-panel]"),
  presetButtons: document.querySelectorAll(".preset-btn"),
};

function setAnswer(name, content) {
  const view = content || {};
  state.currentAnswerState = name;
  state.currentAnswerView = view;

  els.answerPanel.dataset.state = name;
  els.answerPanel.setAttribute("aria-busy", name === "loading" ? "true" : "false");

  els.answerMeta.hidden = !view.meta;
  els.answerMeta.textContent = view.meta || "";

  els.answerTitle.hidden = !view.title;
  els.answerTitle.textContent = view.title || "";

  els.answerStatus.hidden = !view.status;
  els.answerStatus.textContent = view.status || "";

  els.answerBody.hidden = !view.body;
  els.answerBody.textContent = view.body || "";

  els.answerProgress.hidden = name !== "loading";

  els.answerAction.hidden = !view.action;
  if (view.action) {
    els.answerAction.textContent = view.action.label;
    els.answerAction.disabled = Boolean(view.action.disabled);
  }

  els.answerCard.classList.toggle("is-error", name === "error");
  els.answerCard.classList.toggle("is-blocked", name === "blocked");
}

function setBusy(busy) {
  state.busy = busy;
  els.send.disabled = busy || !state.options;
  els.form.setAttribute("aria-busy", busy ? "true" : "false");
}

function setDockOpen(open) {
  state.dockOpen = Boolean(open);
  els.dockToggle.setAttribute("aria-expanded", String(state.dockOpen));
  els.chatControls.hidden = !state.dockOpen;
  if (state.dockOpen && !state.activeFlyout) {
    setFlyout("collections");
  }
}

function setFlyout(target) {
  state.activeFlyout = target;

  const map = [
    { key: "attack", button: els.attackMenu, panel: els.attackPanel },
    { key: "mitigations", button: els.mitigationMenu, panel: els.mitigationPanel },
    { key: "collections", button: els.methodMenu, panel: els.collections },
  ];

  for (const item of map) {
    const open = item.key === target;
    item.button.setAttribute("aria-expanded", String(open));
    item.button.classList.toggle("is-active", open);
    item.panel.hidden = !open;
  }
}

function updateConditionSummary() {
  const collection = state.options ? selectedCollection() : "kb_clean";
  els.summaryCollection.textContent = collection;
  els.summaryCollection.classList.toggle("is-poisoned", collection === "kb_poisoned");

  const boxes = els.mitigationPanel.querySelectorAll('input[type="checkbox"]');
  const activeCount = Array.from(boxes).filter((box) => box.checked).length;

  els.summaryMitigations.textContent = activeCount + " mitigasi";
  els.disableMitigations.disabled = activeCount === 0;
}

function renderCollections(data) {
  els.collections.querySelectorAll(".collection-option").forEach((node) => node.remove());

  for (const name of data.collections) {
    const label = document.createElement("label");
    label.className = "collection-option";

    const input = document.createElement("input");
    input.type = "radio";
    input.name = "collection";
    input.value = name;
    input.checked = name === data.default_collection;
    input.addEventListener("change", updateConditionSummary);

    const text = document.createElement("span");
    text.textContent = name;

    label.append(input, text);
    els.collections.append(label);
  }
}

function renderMitigations(flags) {
  els.mitigationGroups.replaceChildren();
  const available = new Set(flags);
  const rendered = new Set();

  for (const group of MITIGATION_GROUPS) {
    const groupFlags = group.flags.filter((flag) => available.has(flag));
    if (groupFlags.length === 0) {
      continue;
    }

    const section = document.createElement("div");
    section.className = "mitigation-group";

    const heading = document.createElement("p");
    heading.className = "mitigation-group-label";
    heading.textContent = group.label;
    section.append(heading);

    if (group.note) {
      const note = document.createElement("p");
      note.className = "mitigation-group-note";
      note.textContent = group.note;
      section.append(note);
    }

    for (const flag of groupFlags) {
      rendered.add(flag);
      section.append(createMitigationOption(flag));
    }

    els.mitigationGroups.append(section);
  }

  const remaining = flags.filter((flag) => !rendered.has(flag));
  if (remaining.length > 0) {
    const extra = document.createElement("div");
    extra.className = "mitigation-group";

    for (const flag of remaining) {
      extra.append(createMitigationOption(flag));
    }
    els.mitigationGroups.append(extra);
  }
}

function createMitigationOption(flag) {
  const label = document.createElement("label");
  label.className = "mitigation-option";

  const input = document.createElement("input");
  input.type = "checkbox";
  input.dataset.flag = flag;
  input.addEventListener("change", updateConditionSummary);

  const text = document.createElement("span");
  text.textContent = flag;

  label.append(input, text);
  return label;
}

function activeSession() {
  return state.sessions.find((s) => s.id === state.activeSessionId) || null;
}

function ensureActiveSession(firstQuestion) {
  let session = activeSession();
  if (!session) {
    const title =
      firstQuestion.length > 42 ? firstQuestion.slice(0, 42) + "..." : firstQuestion;
    session = {
      id: "sesi-" + state.nextSessionNum++,
      title: title,
      turns: [],
      chunks: [],
      messages: null,
    };
    state.sessions.unshift(session);
    state.activeSessionId = session.id;
  }
  return session;
}

function renderHistory() {
  els.historyList.replaceChildren();

  if (state.sessions.length === 0) {
    const empty = document.createElement("li");
    empty.className = "history-empty";
    empty.textContent = "Belum ada sesi percakapan.";
    els.historyList.append(empty);
    return;
  }

  for (const session of state.sessions.slice(0, 25)) {
    const item = document.createElement("li");
    item.className = "history-item";
    if (session.id === state.activeSessionId) {
      item.classList.add("is-active");
    }

    const button = document.createElement("button");
    button.type = "button";

    const titleSpan = document.createElement("span");
    titleSpan.className = "session-title";
    titleSpan.textContent = session.title;

    const countSpan = document.createElement("span");
    countSpan.className = "session-count";
    countSpan.textContent = String(session.turns.length);

    button.append(titleSpan, countSpan);
    button.addEventListener("click", () => {
      loadSession(session.id);
      setMobilePanel("conversation");
    });

    item.append(button);
    els.historyList.append(item);
  }
}

function buildPastTurnNode(turn) {
  const pair = document.createElement("div");
  pair.className = "turn-pair";

  const userArticle = document.createElement("article");
  userArticle.className = "bubble-user";
  const userP = document.createElement("p");
  userP.textContent = turn.question;
  userArticle.append(userP);

  const assistantGroup = document.createElement("div");
  assistantGroup.className = "assistant-group";

  const label = document.createElement("p");
  label.className = "assistant-label";
  label.textContent = "RAGTrap";
  assistantGroup.append(label);

  if (turn.answerView.meta) {
    const meta = document.createElement("p");
    meta.className = "answer-meta";
    meta.textContent = turn.answerView.meta;
    assistantGroup.append(meta);
  }

  const card = document.createElement("div");
  card.className = "answer-card";
  if (turn.answerState === "error") {
    card.classList.add("is-error");
  } else if (turn.answerState === "blocked") {
    card.classList.add("is-blocked");
  }

  if (turn.answerView.title) {
    const title = document.createElement("h3");
    title.className = "answer-title";
    title.textContent = turn.answerView.title;
    card.append(title);
  }

  if (turn.answerView.status) {
    const status = document.createElement("p");
    status.className = "answer-status";
    status.textContent = turn.answerView.status;
    card.append(status);
  }

  if (turn.answerView.body) {
    const body = document.createElement("p");
    body.className = "answer-body";
    body.textContent = turn.answerView.body;
    card.append(body);
  }

  assistantGroup.append(card);
  pair.append(userArticle, assistantGroup);
  return pair;
}

function renderSessionThread(session) {
  els.pastTurns.replaceChildren();

  if (!session || session.turns.length === 0) {
    els.pastTurns.hidden = true;
    els.questionBubble.hidden = true;
    els.questionText.textContent = "";
    els.conversationHeading.textContent = "Percakapan baru";
    setAnswer("empty", EMPTY_ANSWER);
    clearEvidence();
    return;
  }

  els.conversationHeading.textContent = session.title;
  const previousTurns = session.turns.slice(0, -1);
  const latestTurn = session.turns[session.turns.length - 1];

  if (previousTurns.length > 0) {
    for (const turn of previousTurns) {
      els.pastTurns.append(buildPastTurnNode(turn));
    }
    els.pastTurns.hidden = false;
  } else {
    els.pastTurns.hidden = true;
  }

  state.lastQuestion = latestTurn.question;
  els.questionBubble.hidden = false;
  els.questionText.textContent = latestTurn.question;
  setAnswer(latestTurn.answerState, latestTurn.answerView);

  renderChunks(session.chunks);
  if (session.messages) {
    renderPrompt(session.messages);
  } else {
    els.messages.classList.add("empty");
    els.messages.textContent = "Belum ada prompt.";
    els.copyPrompt.disabled = true;
  }
}

function loadSession(sessionId) {
  if (state.busy) {
    return;
  }
  const session = state.sessions.find((s) => s.id === sessionId);
  if (!session) {
    return;
  }
  state.activeSessionId = session.id;
  renderHistory();
  renderSessionThread(session);
}

function setMobilePanel(target) {
  els.mobileNavButtons.forEach((button) => {
    const active = button.dataset.panelTarget === target;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  els.panels.forEach((panel) => {
    panel.classList.toggle("is-mobile-active", panel.dataset.panel === target);
  });
}

function setTab(tab) {
  state.activeTab = tab;
  const chunksActive = tab === "chunks";

  els.tabChunks.classList.toggle("is-active", chunksActive);
  els.tabChunks.setAttribute("aria-selected", String(chunksActive));
  els.tabPrompt.classList.toggle("is-active", !chunksActive);
  els.tabPrompt.setAttribute("aria-selected", String(!chunksActive));

  els.chunks.hidden = !chunksActive;
  els.promptView.hidden = chunksActive;
}

function renderChunks(chunks) {
  const list = Array.isArray(chunks) ? chunks : [];
  els.chunks.replaceChildren();
  els.chunkCount.textContent = String(list.length);

  if (list.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "Belum ada chunk yang diambil.";
    els.chunks.append(empty);
    return;
  }

  for (const chunk of list) {
    const item = document.createElement("li");
    item.className = "chunk";

    const head = document.createElement("div");
    head.className = "chunk-head";

    const source = document.createElement("span");
    source.className = "chunk-source";
    source.textContent = chunk.source;

    const score = document.createElement("span");
    score.className = "chunk-score";
    score.textContent = "skor " + Number(chunk.score).toFixed(2);

    head.append(source, score);

    const text = document.createElement("p");
    text.className = "chunk-text";
    text.textContent = chunk.text;

    item.append(head, text);
    els.chunks.append(item);
  }
}

function renderPrompt(messages) {
  const list = Array.isArray(messages) ? messages : [];
  const formatted = JSON.stringify(messages ?? null, null, 2);
  state.lastPromptJson = formatted;
  els.messages.classList.remove("empty");
  els.messages.replaceChildren();

  if (list.length === 0) {
    els.messages.textContent = formatted;
  } else {
    for (const msg of list) {
      const card = document.createElement("article");
      card.className = "prompt-msg";

      const role = String(msg && msg.role ? msg.role : "unknown").toLowerCase();
      card.dataset.role = role;

      const head = document.createElement("div");
      head.className = "prompt-msg-head";

      const badge = document.createElement("span");
      badge.className = "prompt-role-badge";
      badge.textContent = role.toUpperCase();
      head.append(badge);

      const body = document.createElement("p");
      body.className = "prompt-msg-body";
      body.textContent = String(msg && msg.content !== undefined ? msg.content : "");

      card.append(head, body);
      els.messages.append(card);
    }
  }

  els.copyPrompt.disabled = false;
  els.copyPrompt.textContent = "Salin JSON";
}

function clearEvidence() {
  renderChunks([]);
  state.lastPromptJson = "";
  els.messages.classList.add("empty");
  els.messages.textContent = "Belum ada prompt.";
  els.copyPrompt.disabled = true;
  els.copyPrompt.textContent = "Salin JSON";
}

function selectedCollection() {
  const checked = els.collections.querySelector('input[name="collection"]:checked');
  return checked ? checked.value : state.options.default_collection;
}

function selectCollectionByName(name) {
  const radio = els.collections.querySelector(`input[name="collection"][value="${name}"]`);
  if (radio) {
    radio.checked = true;
    updateConditionSummary();
  }
}

function selectedFlags() {
  const flags = {};
  els.mitigationPanel.querySelectorAll('input[type="checkbox"]').forEach((box) => {
    flags[box.dataset.flag] = box.checked;
  });
  return flags;
}

function showQuestion(question, session) {
  els.questionBubble.hidden = false;
  els.questionText.textContent = question;
  els.conversationHeading.textContent = session ? session.title : question;
}

function startNewSession() {
  if (state.busy) {
    return;
  }
  state.activeSessionId = null;
  state.lastQuestion = "";
  els.pastTurns.replaceChildren();
  els.pastTurns.hidden = true;
  els.questionBubble.hidden = true;
  els.questionText.textContent = "";
  els.conversationHeading.textContent = "Percakapan baru";
  setAnswer("empty", EMPTY_ANSWER);
  clearEvidence();
  renderHistory();
  els.question.value = "";
  setDockOpen(false);
  setMobilePanel("conversation");
  els.question.focus();
}

function recordSessionTurn(session, question, chunks, messages) {
  if (!session) {
    return;
  }
  const snapshotView = Object.assign({}, state.currentAnswerView);
  if (state.currentAnswerTurnIndex !== undefined && session.turns[state.currentAnswerTurnIndex]) {
    session.turns[state.currentAnswerTurnIndex] = {
      question: question,
      answerState: state.currentAnswerState,
      answerView: snapshotView,
    };
  }
  session.chunks = Array.isArray(chunks) ? chunks : [];
  session.messages = messages || null;
  renderHistory();
}

function showError(status, message, session, question) {
  const copy = ERROR_COPY[status] || {
    meta: "Error: server tidak dapat dihubungi",
    title: "Server tidak dapat dihubungi",
    detail: "Pastikan Flask berjalan di 127.0.0.1:5000, lalu kirim ulang.",
  };

  const body = status === 400 && message ? message : copy.detail;

  setAnswer("error", {
    meta: copy.meta,
    title: copy.title,
    status: status ? "status " + status : "",
    body: body,
    action: { label: "Kirim ulang", disabled: false },
  });

  recordSessionTurn(session, question, [], null);
}

function revealAnswer() {
  if (els.thread.scrollHeight <= els.thread.clientHeight) {
    return;
  }

  const threadTop = els.thread.getBoundingClientRect().top;
  const labelTop = els.assistantLabel.getBoundingClientRect().top;
  els.thread.scrollTop += labelTop - threadTop - 16;
}

function showResult(question, data, collection, session) {
  if (data.blocked_by) {
    const meta = [
      collection,
      data.blocked_by + " aktif",
      Number(data.latency_s).toFixed(2) + " detik",
    ].join(" \u00b7 ");

    setAnswer("blocked", {
      meta: meta,
      title: "diblokir oleh " + data.blocked_by,
      body: "Mitigasi menghentikan permintaan ini. Tidak ada jawaban yang ditampilkan.",
    });
  } else {
    setAnswer("success", { body: data.response || "(jawaban kosong)" });
  }

  renderChunks(data.chunks);
  renderPrompt(data.messages);
  recordSessionTurn(session, question, data.chunks, data.messages);

  revealAnswer();
}

async function submitQuestion(rawQuestion, options) {
  const settings = options || {};
  const question = String(rawQuestion || "").trim();

  if (state.busy || question === "") {
    els.question.focus();
    return;
  }

  setDockOpen(false);
  const session = ensureActiveSession(question);

  if (!settings.retry) {
    if (session.turns.length > 0) {
      const completedTurn = session.turns[session.turns.length - 1];
      els.pastTurns.append(buildPastTurnNode(completedTurn));
      els.pastTurns.hidden = false;
    }
    session.turns.push({
      question: question,
      answerState: "loading",
      answerView: LOADING_ANSWER,
    });
    state.currentAnswerTurnIndex = session.turns.length - 1;
    els.question.value = "";
  } else {
    state.currentAnswerTurnIndex = Math.max(0, session.turns.length - 1);
  }

  state.lastQuestion = question;
  setBusy(true);
  showQuestion(question, session);
  setAnswer("loading", LOADING_ANSWER);
  clearEvidence();
  renderHistory();

  const payload = {
    question: question,
    collection: selectedCollection(),
    flags: selectedFlags(),
  };

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      showError(response.status, data.error, session, question);
      return;
    }

    showResult(question, data, payload.collection, session);
  } catch (error) {
    showError(0, error.message, session, question);
  } finally {
    setBusy(false);
  }
}

async function loadOptions() {
  try {
    const response = await fetch("/api/options", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("GET /api/options gagal (" + response.status + ")");
    }

    const data = await response.json();
    state.options = data;
    els.modelName.textContent = data.chat_model;
    els.question.maxLength = data.max_question_chars;
    renderCollections(data);
    renderMitigations(data.mitigations);
    updateConditionSummary();
    els.send.disabled = false;
    setAnswer("empty", EMPTY_ANSWER);
    els.question.focus();
  } catch (error) {
    showError(0, error.message, null, "");
  }
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitQuestion(els.question.value);
});

els.answerAction.addEventListener("click", () => {
  if (state.lastQuestion) {
    submitQuestion(state.lastQuestion, { retry: true });
  }
});

els.dockToggle.addEventListener("click", () => {
  setDockOpen(!state.dockOpen);
});

els.attackMenu.addEventListener("click", () => setFlyout("attack"));
els.mitigationMenu.addEventListener("click", () => setFlyout("mitigations"));
els.methodMenu.addEventListener("click", () => setFlyout("collections"));

els.presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const targetCollection = button.dataset.presetCollection;
    const presetQuestion = button.dataset.presetQuestion;
    if (targetCollection) {
      selectCollectionByName(targetCollection);
    }
    if (presetQuestion) {
      els.question.value = presetQuestion;
    }
    setDockOpen(false);
    els.question.focus();
  });
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.dockOpen) {
    setDockOpen(false);
    els.dockToggle.focus();
  }
});

document.addEventListener("click", (event) => {
  if (
    state.dockOpen &&
    !els.chatControls.contains(event.target) &&
    !els.dockToggle.contains(event.target)
  ) {
    setDockOpen(false);
  }
});

els.disableMitigations.addEventListener("click", () => {
  els.mitigationPanel.querySelectorAll('input[type="checkbox"]').forEach((box) => {
    box.checked = false;
  });
  updateConditionSummary();
});

els.resetChat.addEventListener("click", startNewSession);

els.tabChunks.addEventListener("click", () => setTab("chunks"));
els.tabPrompt.addEventListener("click", () => setTab("prompt"));

[els.tabChunks, els.tabPrompt].forEach((tabEl) => {
  tabEl.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      event.preventDefault();
      const next = state.activeTab === "chunks" ? "prompt" : "chunks";
      setTab(next);
      (next === "chunks" ? els.tabChunks : els.tabPrompt).focus();
    }
  });
});

els.copyPrompt.addEventListener("click", async () => {
  if (!state.lastPromptJson) {
    return;
  }
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(state.lastPromptJson);
      els.copyPrompt.textContent = "Tersalin";
    }
  } catch {
    els.copyPrompt.textContent = "Gagal";
  }
  window.setTimeout(() => {
    if (!els.copyPrompt.disabled) {
      els.copyPrompt.textContent = "Salin JSON";
    }
  }, 1600);
});

els.mobileNavButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setMobilePanel(button.dataset.panelTarget);
  });
});

setTab("chunks");
renderHistory();
loadOptions();
