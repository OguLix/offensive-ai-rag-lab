"use strict";

const state = {
  options: null,
  busy: false,
};

const els = {
  form: document.getElementById("chat-form"),
  question: document.getElementById("question"),
  collection: document.getElementById("collection"),
  mitigations: document.getElementById("mitigations"),
  send: document.getElementById("send"),
  status: document.getElementById("status"),
  blocked: document.getElementById("blocked"),
  answer: document.getElementById("answer"),
  chunks: document.getElementById("chunks"),
  messages: document.getElementById("messages"),
};

function setStatus(message, kind) {
  els.status.textContent = message;
  els.status.dataset.kind = kind || "info";
}

function labelFor(flag) {
  return flag.replaceAll("_", " ");
}

function renderOptions(data) {
  els.collection.replaceChildren();
  for (const name of data.collections) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    if (name === data.default_collection) {
      option.selected = true;
    }
    els.collection.append(option);
  }

  els.mitigations.querySelectorAll("label").forEach((node) => node.remove());
  for (const flag of data.mitigations) {
    const label = document.createElement("label");
    label.className = "toggle";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.dataset.flag = flag;

    const text = document.createElement("span");
    text.textContent = labelFor(flag);

    label.append(checkbox, text);
    els.mitigations.append(label);
  }

  els.question.maxLength = data.max_question_chars;
  els.send.disabled = false;
  els.question.focus();
}

async function loadOptions() {
  try {
    const response = await fetch("/api/options", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("GET /api/options gagal (" + response.status + ")");
    }
    const data = await response.json();
    state.options = data;
    renderOptions(data);
    setStatus(
      "Siap. Model: " + data.chat_model + ". Pipeline masih stub Fase 0, jadi permintaan akan dijawab 501.",
      "info",
    );
  } catch (error) {
    setStatus("Tidak bisa memuat opsi: " + error.message, "error");
    els.send.disabled = true;
  }
}

function setBusy(busy, message) {
  state.busy = busy;
  els.send.disabled = busy || !state.options;
  els.send.textContent = busy ? "Memproses..." : "Kirim";
  els.form.setAttribute("aria-busy", busy ? "true" : "false");
  if (message) {
    setStatus(message, busy ? "loading" : "info");
  }
}

function renderResult(data) {
  els.answer.classList.remove("empty");
  els.answer.textContent = data.response || "(jawaban kosong)";

  if (data.blocked_by) {
    els.blocked.hidden = false;
    els.blocked.textContent = "Diblokir oleh mitigasi: " + data.blocked_by;
  } else {
    els.blocked.hidden = true;
    els.blocked.textContent = "";
  }

  els.chunks.replaceChildren();
  if (!Array.isArray(data.chunks) || data.chunks.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "Tidak ada chunk yang diambil.";
    els.chunks.append(empty);
  } else {
    for (const chunk of data.chunks) {
      const item = document.createElement("li");
      item.className = "chunk";

      const header = document.createElement("p");
      header.className = "chunk-header";
      header.textContent =
        chunk.doc_id + " · skor " + Number(chunk.score).toFixed(3) + " · " + chunk.source;

      const body = document.createElement("p");
      body.className = "chunk-text";
      body.textContent = chunk.text;

      item.append(header, body);
      els.chunks.append(item);
    }
  }

  els.messages.classList.remove("empty");
  els.messages.textContent = JSON.stringify(data.messages, null, 2);
}

async function onSubmit(event) {
  event.preventDefault();
  if (state.busy) {
    return;
  }

  const question = els.question.value.trim();
  if (!question) {
    setStatus("Pertanyaan masih kosong.", "error");
    els.question.focus();
    return;
  }

  const flags = {};
  els.mitigations.querySelectorAll("input[type=checkbox]").forEach((box) => {
    flags[box.dataset.flag] = box.checked;
  });

  setBusy(true, "Mengirim permintaan... generasi di CPU bisa lambat.");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        question: question,
        collection: els.collection.value,
        flags: flags,
      }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      setStatus(data.error || "Permintaan gagal (" + response.status + ").", "error");
      return;
    }

    renderResult(data);
    setStatus("Selesai dalam " + Number(data.latency_s).toFixed(2) + " detik.", "info");
  } catch (error) {
    setStatus("Gagal menghubungi server: " + error.message, "error");
  } finally {
    setBusy(false);
  }
}

els.form.addEventListener("submit", onSubmit);
loadOptions();
