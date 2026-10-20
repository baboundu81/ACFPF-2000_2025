// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright (C) 2026 ACFPF contributors

(() => {
  const form = document.getElementById("ask-form");
  const result = document.getElementById("ask-result");
  const progress = document.getElementById("research-progress");
  const progressStatus = document.getElementById("research-progress-status");
  const progressSteps = document.getElementById("research-progress-steps");
  if (!form || !result || !progress || !progressStatus || !progressSteps) return;

  const button = form.querySelector("button[type='submit']");
  const question = document.getElementById("ask-question");

  const paragraph = (text, className) => {
    const node = document.createElement("p");
    node.textContent = text;
    if (className) node.className = className;
    return node;
  };

  const resetResearch = () => {
    result.replaceChildren();
    result.hidden = true;
    progressSteps.replaceChildren();
    progressStatus.textContent = "Préparation des données et des sources…";
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

  const renderResearchEvent = (event) => {
    if (event.type === "started") {
      progressStatus.textContent = event.message || "Préparation…";
      return;
    }
    if (event.type === "search") {
      progressStatus.textContent = "Recherche de documents officiels…";
      const sources = Array.isArray(event.source_ids) ? event.source_ids.join(", ") : "sources autorisées";
      addStep("Recherche", `“${event.query}” · ${sources} · ${event.result_count || 0} résultat(s)`);
      return;
    }
    if (event.type === "open") {
      progressStatus.textContent = "Lecture des sources…";
      addStep(
        "Ouverture",
        `${event.source_id} · ${event.title} · ${event.locator}`,
        event.url,
      );
      return;
    }
    if (event.type === "read") {
      progressStatus.textContent = "Approfondissement du document…";
      addStep("Lecture", `${event.document_id} · ${event.locator} · preuve ${event.evidence_id}`);
      return;
    }
    if (event.type === "notice") {
      addStep("Information", event.message || "Une étape de recherche n'a pas abouti.");
      return;
    }
    if (event.type === "error") {
      progressStatus.textContent = "Recherche interrompue";
      addStep("Erreur", event.message || "La recherche a échoué.");
    }
  };

  const renderAnswer = (payload) => {
    result.replaceChildren();
    result.hidden = false;
    progressStatus.textContent = "Enquête terminée";

    const label = payload.status === "insufficient" ? "Preuves insuffisantes" : "Réponse ACFPF";
    result.appendChild(paragraph(label, "eyebrow"));
    result.appendChild(paragraph(payload.answer, "ask-result__answer"));

    if (Array.isArray(payload.citations) && payload.citations.length > 0) {
      result.appendChild(paragraph("Preuves utilisées", "ask-result__subtitle"));
      const list = document.createElement("ul");
      payload.citations.forEach((citation) => {
        const li = document.createElement("li");
        const link = document.createElement("a");
        link.href = citation.source_url;
        link.target = "_blank";
        link.rel = "noreferrer";
        const locator = citation.locator ? ` · ${citation.locator}` : "";
        const origin = citation.source_id ? `${citation.source_id} · ` : "";
        link.textContent = `${citation.id} · ${origin}${citation.label}${locator}`;
        li.appendChild(link);
        if (citation.retrieved_at) {
          const meta = document.createElement("span");
          meta.className = "ask-result__citation-meta";
          meta.textContent = ` consulté ${new Date(citation.retrieved_at).toLocaleString("fr-FR")}`;
          li.appendChild(meta);
        }
        list.appendChild(li);
      });
      result.appendChild(list);
    }

    if (Array.isArray(payload.limitations) && payload.limitations.length > 0) {
      result.appendChild(paragraph("Limites", "ask-result__subtitle"));
      const list = document.createElement("ul");
      payload.limitations.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        list.appendChild(li);
      });
      result.appendChild(list);
    }

    result.appendChild(
      paragraph(`Modèle : ${payload.provider} / ${payload.model}`, "ask-result__technical"),
    );
  };

  const renderError = (message) => {
    result.replaceChildren();
    result.hidden = false;
    result.appendChild(paragraph("Erreur", "eyebrow"));
    result.appendChild(paragraph(message, "ask-result__answer"));
  };

  const consumeStream = async (response) => {
    if (!response.body) throw new Error("Réponse de recherche non diffusable.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.type === "answer") renderAnswer(event.answer);
        else if (event.type === "error") {
          renderResearchEvent(event);
          renderError(event.message || "La recherche a échoué.");
        } else renderResearchEvent(event);
      }
      if (done) break;
    }

    if (buffer.trim()) {
      const event = JSON.parse(buffer);
      if (event.type === "answer") renderAnswer(event.answer);
      else renderResearchEvent(event);
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = question.value.trim();
    if (!value) return;

    button.disabled = true;
    button.textContent = "Enquête en cours…";
    resetResearch();

    try {
      const response = await fetch("/api/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: value }),
      });
      if (!response.ok) {
        const payload = await response.json();
        renderError(payload.message || "La réponse IA a échoué.");
        return;
      }
      await consumeStream(response);
    } catch (_error) {
      renderError("Impossible de mener la recherche. Vérifiez la connexion et le serveur ACFPF.");
    } finally {
      button.disabled = false;
      button.textContent = "Rechercher et analyser";
    }
  });
})();
