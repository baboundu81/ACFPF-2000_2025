// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright (C) 2026 ACFPF contributors

(() => {
  const form = document.getElementById("dossier-chat-form");
  const thread = document.getElementById("dossier-chat-thread");
  const question = document.getElementById("dossier-chat-question");
  const progress = document.getElementById("research-progress");
  const progressStatus = document.getElementById("research-progress-status");
  const progressSteps = document.getElementById("research-progress-steps");
  if (!form || !thread || !question || !progress || !progressStatus || !progressSteps) return;

  const button = form.querySelector("button[type='submit']");
  const dossierId = form.dataset.dossierId;
  const history = [];

  const addParagraph = (parent, text, className) => {
    const node = document.createElement("p");
    node.textContent = text;
    if (className) node.className = className;
    parent.appendChild(node);
    return node;
  };

  const addMessage = (role, text, payload = null) => {
    const message = document.createElement("article");
    message.className = `chat-message chat-message--${role}`;
    addParagraph(message, text, role === "assistant" ? "chat-message__answer" : "");

    if (payload && Array.isArray(payload.citations) && payload.citations.length > 0) {
      const sources = document.createElement("div");
      sources.className = "chat-message__sources";
      addParagraph(sources, "Sources utilisées");
      const list = document.createElement("ul");
      payload.citations.forEach((citation) => {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = citation.source_url;
        link.target = "_blank";
        link.rel = "noreferrer";
        const locator = citation.locator ? ` · ${citation.locator}` : "";
        link.textContent = `${citation.id} · ${citation.label}${locator}`;
        item.appendChild(link);
        list.appendChild(item);
      });
      sources.appendChild(list);
      message.appendChild(sources);
    }

    if (payload && Array.isArray(payload.limitations) && payload.limitations.length > 0) {
      addParagraph(message, `Limites : ${payload.limitations.join(" · ")}`, "chat-message__meta");
    }
    if (payload && payload.provider && payload.model) {
      addParagraph(message, `${payload.provider} / ${payload.model}`, "chat-message__meta");
    }

    thread.appendChild(message);
    message.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  const resetProgress = () => {
    progressSteps.replaceChildren();
    progressStatus.textContent = "Préparation des sources officielles…";
    progress.hidden = false;
  };

  const addStep = (label, detail, url) => {
    const item = document.createElement("li");
    const head = document.createElement("strong");
    head.textContent = label;
    item.appendChild(head);
    if (detail) item.appendChild(document.createTextNode(` ${detail}`));
    if (url) {
      const link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = "ouvrir";
      item.appendChild(document.createTextNode(" · "));
      item.appendChild(link);
    }
    progressSteps.appendChild(item);
  };

  const renderEvent = (event) => {
    if (event.type === "started") {
      progressStatus.textContent = event.message || "Préparation…";
    } else if (event.type === "search") {
      progressStatus.textContent = "Recherche dans les sources officielles…";
      addStep("Recherche", `“${event.query}” · ${event.result_count || 0} résultat(s)`);
    } else if (event.type === "open") {
      progressStatus.textContent = "Lecture des documents…";
      addStep("Ouverture", `${event.source_id} · ${event.title} · ${event.locator}`, event.url);
    } else if (event.type === "read") {
      progressStatus.textContent = "Approfondissement du document…";
      addStep("Lecture", `${event.document_id} · ${event.locator}`);
    } else if (event.type === "notice") {
      addStep("Information", event.message || "Une étape n'a pas abouti.");
    } else if (event.type === "error") {
      progressStatus.textContent = "Recherche interrompue";
      addStep("Erreur", event.message || "La recherche a échoué.");
    }
  };

  const consumeStream = async (response) => {
    if (!response.body) throw new Error("Réponse non diffusable.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalAnswer = null;

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.type === "answer") finalAnswer = event.answer;
        else renderEvent(event);
      }
      if (done) break;
    }
    if (buffer.trim()) {
      const event = JSON.parse(buffer);
      if (event.type === "answer") finalAnswer = event.answer;
      else renderEvent(event);
    }
    return finalAnswer;
  };

  const ask = async (value) => {
    const recentHistory = history.slice(-2);
    history.push({ role: "user", content: value });
    addMessage("user", value);
    resetProgress();
    button.disabled = true;
    button.textContent = "Recherche en cours…";

    try {
      const response = await fetch("/api/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: value,
          dossier_id: dossierId,
          history: recentHistory,
        }),
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.message || "La réponse IA a échoué.");
      }
      const answer = await consumeStream(response);
      if (!answer) throw new Error("La recherche n'a produit aucune réponse finale.");
      progressStatus.textContent = "Enquête terminée";
      addMessage("assistant", answer.answer, answer);
      history.push({ role: "assistant", content: answer.answer });
    } catch (error) {
      addMessage("assistant", error.message || "Impossible de mener la recherche.");
    } finally {
      button.disabled = false;
      button.textContent = "Rechercher et répondre";
      question.focus();
    }
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = question.value.trim();
    if (!value) return;
    question.value = "";
    ask(value);
  });

  document.querySelectorAll("[data-question]").forEach((preset) => {
    preset.addEventListener("click", () => {
      question.value = preset.dataset.question || "";
      question.focus();
    });
  });
})();
