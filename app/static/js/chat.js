"use strict";

const EMPTY_ANSWER = {
  title: "Belum ada jawaban",
  body: "Atur kondisi uji di panel kontrol, tulis pertanyaan, lalu pilih Kirim ke chatbot.",
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

const state = {
  options: null,
  busy: false,
  history: [],
  lastQuestion: "",
  activeTab: "chunks",
};

const els = {
  modelName: document.getElementById("model-name"),
  historyList: document.getElementById("history-list"),
  disableMitigations: document.getElementById("disable-mitigations"),
  conversationHeading: document.getElementById("conversation-heading"),
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
  mitigationPanel: document.getElementById("mitigation-panel"),
  collections: document.getElementById("collections"),
  form: document.getElementById("chat-form"),
  question: document.getElementById("question"),
  send: document.getElementById("send"),
  tabChunks: document.getElementById("tab-chunks"),
  tabPrompt: document.getElementById("tab-prompt"),
  chunks: document.getElementById("chunks"),
  messages: document.getElementById("messages"),
  chunkCount: document.getElementById("chunk-count"),
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
  els.form.setAttribute("aria-busy", busy ? "true" : "false");
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

    const text = document.createElement("span");
    text.textContent = name;

    label.append(input, text);
    els.collections.append(label);
  }
}

function renderMitigations(flags) {
  els.mitigationPanel.querySelectorAll(".mitigation-option").forEach((node) => node.remove());

  for (const flag of flags) {
    const label = document.createElement("label");
    label.className = "mitigation-option";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.dataset.flag = flag;

    const text = document.createElement("span");
    text.textContent = flag.replaceAll("_", " ");

    label.append(input, text);
    els.mitigationPanel.append(label);
  }
}

function renderHistory() {
  els.historyList.replaceChildren();

  if (state.history.length === 0) {
    const empty = document.createElement("li");
    empty.className = "history-empty";
    empty.textContent = "Belum ada riwayat.";
    els.historyList.append(empty);
    return;
  }

  for (const question of state.history.slice(0, 20)) {
    const item = document.createElement("li");
    item.className = "history-item";

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = question;
    button.addEventListener("click", () => {
      els.question.value = question;
      els.question.focus();
    });

    item.append(button);
    els.historyList.append(item);
  }
}

function addHistory(question) {
  state.history.unshift(question);
  renderHistory();
}

function setTab(tab) {
  state.activeTab = tab;
  const chunksActive = tab === "chunks";

  els.tabChunks.classList.toggle("is-active", chunksActive);
  els.tabChunks.setAttribute("aria-selected", String(chunksActive));
  els.tabPrompt.classList.toggle("is-active", !chunksActive);
  els.tabPrompt.setAttribute("aria-selected", String(!chunksActive));

  els.chunks.hidden = !chunksActive;
  els.messages.hidden = chunksActive;
}

function renderChunks(chunks) {
  const list = Array.isArray(chunks) ? chunks : [];
  els.chunks.replaceChildren();
  els.chunkCount.textContent = "「" + list.length + "」";

  if (list.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "Belum ada chunk.";
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
  els.messages.classList.remove("empty");
  els.messages.textContent = JSON.stringify(messages ?? null, null, 2);
}

function clearEvidence() {
  renderChunks([]);
  els.messages.classList.add("empty");
  els.messages.textContent = "Belum ada prompt.";
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
  els.conversationHeading.textContent =
    question.length > 60 ? question.slice(0, 60) + "..." : question;
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

function showResult(question, data, collection) {
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

  revealAnswer();
}

async function submitQuestion(rawQuestion, options) {
  const settings = options || {};
  const question = String(rawQuestion || "").trim();

  if (state.busy || question === "") {
    els.question.focus();
    return;
  }

  state.lastQuestion = question;
  setBusy(true);
  showQuestion(question);
  setAnswer("loading", LOADING_ANSWER);
  clearEvidence();

  if (!settings.retry) {
    addHistory(question);
  }

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
      showError(response.status, data.error);
      return;
    }

    showResult(question, data, payload.collection);
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

els.answerAction.addEventListener("click", () => {
  if (state.lastQuestion) {
    submitQuestion(state.lastQuestion, { retry: true });
  }
});

els.mitigationMenu.addEventListener("click", () => {
  const expanded = els.mitigationMenu.getAttribute("aria-expanded") === "true";
  els.mitigationMenu.setAttribute("aria-expanded", String(!expanded));
  els.mitigationPanel.hidden = expanded;
});

els.disableMitigations.addEventListener("click", () => {
  els.mitigationPanel.querySelectorAll('input[type="checkbox"]').forEach((box) => {
    box.checked = false;
  });
});

els.tabChunks.addEventListener("click", () => setTab("chunks"));
els.tabPrompt.addEventListener("click", () => setTab("prompt"));

setTab("chunks");
renderHistory();
loadOptions();
