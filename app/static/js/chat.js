"use strict";

const EMPTY_ANSWER = {
  title: "Belum ada jawaban",
  body: "Atur koleksi dan mitigasi di bagian [3], tulis pertanyaan, lalu pilih Kirim ke chatbot.",
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
    label: "M3 Asal dokumen",
    flags: ["ingest_sanitizer", "provenance_check"],
  },
];

const state = {
  options: null,
  busy: false,
  history: [],
  lastQuestion: "",
  lastPromptJson: "",
  activeTab: "chunks",
};

const els = {
  modelName: document.getElementById("model-name"),
  historyList: document.getElementById("history-list"),
  summaryCollection: document.getElementById("summary-collection"),
  summaryMitigations: document.getElementById("summary-mitigations"),
  disableMitigations: document.getElementById("disable-mitigations"),
  resetChat: document.getElementById("reset-chat"),
  conversationHeading: document.getElementById("conversation-heading"),
  conversationTitleText: document.getElementById("conversation-title-text"),
  runSummary: document.getElementById("run-summary"),
  assistantLabel: document.querySelector(".assistant-label"),
  thread: document.getElementById("thread"),
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
  mitigationMenu: document.getElementById("mitigation-menu"),
  mitigationCount: document.getElementById("mitigation-count"),
  mitigationPanel: document.getElementById("mitigation-panel"),
  mitigationGroups: document.getElementById("mitigation-groups"),
  closeMitigationPanel: document.getElementById("close-mitigation-panel"),
  collections: document.getElementById("collections"),
  form: document.getElementById("chat-form"),
  question: document.getElementById("question"),
  charCounter: document.getElementById("char-counter"),
  send: document.getElementById("send"),
  tabChunks: document.getElementById("tab-chunks"),
  tabPrompt: document.getElementById("tab-prompt"),
  chunks: document.getElementById("chunks"),
  promptView: document.getElementById("prompt-view"),
  messages: document.getElementById("messages"),
  copyPrompt: document.getElementById("copy-prompt"),
  chunkCount: document.getElementById("chunk-count"),
  mobileNavButtons: document.querySelectorAll(".mobile-nav-btn"),
  panels: document.querySelectorAll(".panel[data-panel]"),
};

function setAnswer(name, content) {
  const view = content || {};
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
  els.send.textContent = busy ? "Menunggu jawaban" : "Kirim ke chatbot";
  els.form.setAttribute("aria-busy", busy ? "true" : "false");
}

function updateCharCounter() {
  const limit = state.options ? state.options.max_question_chars : 2000;
  els.charCounter.textContent = els.question.value.length + " / " + limit;
}

function updateConditionSummary() {
  const collection = state.options ? selectedCollection() : "memuat...";
  els.summaryCollection.textContent = collection;
  els.summaryCollection.classList.toggle("is-warning", collection === "kb_poisoned");

  const boxes = els.mitigationPanel.querySelectorAll('input[type="checkbox"]');
  const activeCount = Array.from(boxes).filter((box) => box.checked).length;

  els.summaryMitigations.textContent = activeCount + " aktif";
  els.mitigationCount.textContent = activeCount + " aktif";
  els.mitigationCount.classList.toggle("has-active", activeCount > 0);
  els.disableMitigations.disabled = activeCount === 0;
}

function setMitigationPanelOpen(open) {
  els.mitigationMenu.setAttribute("aria-expanded", String(open));
  els.mitigationPanel.hidden = !open;
}

function renderCollections(data) {
  els.collections.querySelectorAll(".collection-option").forEach((node) => node.remove());

  for (const name of data.collections) {
    const label = document.createElement("label");
    label.className = "collection-option";
    if (name === "kb_poisoned") {
      label.classList.add("is-poisoned");
    }

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

    const heading = document.createElement("p");
    heading.className = "mitigation-group-label";
    heading.textContent = "Mitigasi lainnya";
    extra.append(heading);

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

function renderHistory() {
  els.historyList.replaceChildren();

  if (state.history.length === 0) {
    const empty = document.createElement("li");
    empty.className = "history-empty";
    empty.textContent =
      "Belum ada riwayat. Kirim pertanyaan pertama untuk menyimpannya di sesi ini.";
    els.historyList.append(empty);
    return;
  }

  for (const entry of state.history.slice(0, 20)) {
    const item = document.createElement("li");
    item.className = "history-item";

    const button = document.createElement("button");
    button.type = "button";

    const questionLine = document.createElement("span");
    questionLine.className = "history-question";
    questionLine.textContent = entry.question;

    const metaLine = document.createElement("span");
    metaLine.className = "history-meta";
    metaLine.textContent = entry.collection + " · " + entry.activeMitigations + " mitigasi";

    button.append(questionLine, metaLine);
    button.addEventListener("click", () => {
      els.question.value = entry.question;
      updateCharCounter();
      setMobilePanel("conversation");
      els.question.focus();
    });

    item.append(button);
    els.historyList.append(item);
  }
}

function addHistory(question, collection, flags) {
  const activeMitigations = Object.values(flags).filter(Boolean).length;
  state.history.unshift({ question, collection, activeMitigations });
  renderHistory();
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
  els.chunkCount.textContent = "[" + list.length + "]";

  if (list.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent =
      "Belum ada chunk. Kirim pertanyaan untuk melihat dokumen yang diambil retriever.";
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
    source.textContent = chunk.source || chunk.doc_id || "(sumber tidak diketahui)";

    const numericScore = Number(chunk.score);
    const clampedScore = Number.isFinite(numericScore)
      ? Math.max(0, Math.min(1, numericScore))
      : 0;

    const score = document.createElement("span");
    score.className = "chunk-score";
    score.textContent = "skor " + (Number.isFinite(numericScore) ? numericScore.toFixed(2) : "0.00");

    head.append(source, score);

    const tags = document.createElement("div");
    tags.className = "chunk-tags";

    const bar = document.createElement("div");
    bar.className = "chunk-bar";
    const fill = document.createElement("span");
    fill.className = "chunk-bar-fill";
    fill.style.width = Math.round(clampedScore * 100) + "%";
    bar.append(fill);
    tags.append(bar);

    if (String(chunk.source || "").includes("poisoned")) {
      const flag = document.createElement("span");
      flag.className = "chunk-flag";
      flag.textContent = "poisoned";
      tags.append(flag);
    }

    const text = document.createElement("p");
    text.className = "chunk-text";
    text.textContent = chunk.text;

    item.append(head, tags, text);
    els.chunks.append(item);
  }
}

function renderPrompt(messages) {
  const formatted = JSON.stringify(messages ?? null, null, 2);
  state.lastPromptJson = formatted;
  els.messages.classList.remove("empty");
  els.messages.textContent = formatted;
  els.copyPrompt.disabled = false;
  els.copyPrompt.textContent = "Salin JSON";
}

function clearEvidence() {
  renderChunks([]);
  state.lastPromptJson = "";
  els.messages.classList.add("empty");
  els.messages.textContent =
    "Belum ada prompt. Kirim pertanyaan untuk memeriksa prompt akhir.";
  els.copyPrompt.disabled = true;
  els.copyPrompt.textContent = "Salin JSON";
}

function selectedCollection() {
  const checked = els.collections.querySelector('input[name="collection"]:checked');
  return checked ? checked.value : state.options.default_collection;
}

function selectedFlags() {
  const flags = {};
  els.mitigationPanel.querySelectorAll('input[type="checkbox"]').forEach((box) => {
    flags[box.dataset.flag] = box.checked;
  });
  return flags;
}

function showQuestion(question) {
  els.questionBubble.hidden = false;
  els.questionText.textContent = question;
  els.conversationTitleText.textContent =
    question.length > 60 ? question.slice(0, 60) + "..." : question;
}

function resetConversation() {
  if (state.busy) {
    return;
  }
  state.lastQuestion = "";
  els.questionBubble.hidden = true;
  els.questionText.textContent = "";
  els.conversationTitleText.textContent = "Percakapan baru";
  els.runSummary.hidden = true;
  els.runSummary.textContent = "";
  setAnswer("empty", EMPTY_ANSWER);
  clearEvidence();
  els.question.value = "";
  updateCharCounter();
  setMobilePanel("conversation");
  els.question.focus();
}

function showError(status, message) {
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
}

function revealAnswer() {
  if (els.thread.scrollHeight <= els.thread.clientHeight) {
    return;
  }

  const threadTop = els.thread.getBoundingClientRect().top;
  const labelTop = els.assistantLabel.getBoundingClientRect().top;
  els.thread.scrollTop += labelTop - threadTop - 16;
}

function showResult(question, data, collection, flags) {
  const activeCount = Object.values(flags).filter(Boolean).length;
  const latencyText = Number(data.latency_s).toFixed(2) + " detik";

  els.runSummary.hidden = false;
  els.runSummary.textContent = collection + " · " + latencyText;

  if (data.blocked_by) {
    const meta = [
      collection,
      data.blocked_by + " aktif",
      latencyText,
    ].join(" \u00b7 ");

    setAnswer("blocked", {
      meta: meta,
      title: "diblokir oleh " + data.blocked_by,
      body: "Mitigasi menghentikan permintaan ini. Tidak ada jawaban yang ditampilkan.",
    });
  } else {
    const meta = [
      collection,
      activeCount + " mitigasi aktif",
      latencyText,
    ].join(" \u00b7 ");

    setAnswer("success", {
      meta: meta,
      body: data.response || "(jawaban kosong)",
    });
  }

  renderChunks(data.chunks);
  renderPrompt(data.messages);

  revealAnswer();
}

async function submitQuestion(rawQuestion, options) {
  const settings = options || {};
  const question = String(rawQuestion || "").trim();

  if (state.busy || question === "") {
    els.question.focus();
    return;
  }

  const collection = selectedCollection();
  const flags = selectedFlags();

  setMitigationPanelOpen(false);
  state.lastQuestion = question;
  setBusy(true);
  showQuestion(question);
  els.runSummary.hidden = true;
  setAnswer("loading", LOADING_ANSWER);
  clearEvidence();

  if (!settings.retry) {
    addHistory(question, collection, flags);
  }

  const payload = {
    question: question,
    collection: collection,
    flags: flags,
  };

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      showError(response.status, data.error);
      return;
    }

    showResult(question, data, payload.collection, payload.flags);
  } catch (error) {
    showError(0, error.message);
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
    updateCharCounter();
    updateConditionSummary();
    els.send.disabled = false;
    setAnswer("empty", EMPTY_ANSWER);
    els.question.focus();
  } catch (error) {
    showError(0, error.message);
  }
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitQuestion(els.question.value);
});

els.question.addEventListener("input", updateCharCounter);

els.answerAction.addEventListener("click", () => {
  if (state.lastQuestion) {
    submitQuestion(state.lastQuestion, { retry: true });
  }
});

els.mitigationMenu.addEventListener("click", () => {
  const expanded = els.mitigationMenu.getAttribute("aria-expanded") === "true";
  setMitigationPanelOpen(!expanded);
});

els.closeMitigationPanel.addEventListener("click", () => {
  setMitigationPanelOpen(false);
  els.mitigationMenu.focus();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.mitigationPanel.hidden) {
    setMitigationPanelOpen(false);
    els.mitigationMenu.focus();
  }
});

document.addEventListener("click", (event) => {
  if (
    !els.mitigationPanel.hidden &&
    !els.mitigationPanel.contains(event.target) &&
    !els.mitigationMenu.contains(event.target)
  ) {
    setMitigationPanelOpen(false);
  }
});

els.disableMitigations.addEventListener("click", () => {
  els.mitigationPanel.querySelectorAll('input[type="checkbox"]').forEach((box) => {
    box.checked = false;
  });
  updateConditionSummary();
});

els.resetChat.addEventListener("click", resetConversation);

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
    } else {
      els.copyPrompt.textContent = "Clipboard tidak tersedia";
    }
  } catch {
    els.copyPrompt.textContent = "Gagal menyalin";
  }
  window.setTimeout(() => {
    if (!els.copyPrompt.disabled) {
      els.copyPrompt.textContent = "Salin JSON";
    }
  }, 1800);
});

els.mobileNavButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setMobilePanel(button.dataset.panelTarget);
  });
});

setTab("chunks");
renderHistory();
updateCharCounter();
loadOptions();
