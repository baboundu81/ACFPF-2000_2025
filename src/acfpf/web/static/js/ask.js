// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright (C) 2026 ACFPF contributors

(() => {
  const form = document.getElementById("ask-form");
  const result = document.getElementById("ask-result");
  if (!form || !result) return;

  const button = form.querySelector("button[type='submit']");
  const question = document.getElementById("ask-question");

  const clear = () => {
    result.replaceChildren();
    result.hidden = false;
  };

  const paragraph = (text, className) => {
    const node = document.createElement("p");
    node.textContent = text;
    if (className) node.className = className;
    return node;
  };

  const renderAnswer = (payload) => {
    clear();
    const label = payload.status === "insufficient" ? "Contexte insuffisant" : "Réponse ACFPF";
    result.appendChild(paragraph(label, "eyebrow"));
    result.appendChild(paragraph(payload.answer, "ask-result__answer"));

    if (Array.isArray(payload.limitations) && payload.limitations.length > 0) {
      const title = paragraph("Limites", "ask-result__subtitle");
      result.appendChild(title);
      const list = document.createElement("ul");
      payload.limitations.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        list.appendChild(li);
      });
      result.appendChild(list);
    }

    if (Array.isArray(payload.citations) && payload.citations.length > 0) {
      result.appendChild(paragraph("Sources utilisées", "ask-result__subtitle"));
      const list = document.createElement("ul");
      payload.citations.forEach((citation) => {
        const li = document.createElement("li");
        const link = document.createElement("a");
        link.href = citation.source_url;
        link.target = "_blank";
        link.rel = "noreferrer";
        link.textContent = `${citation.id} · ${citation.dataset_code} — ${citation.label}`;
        li.appendChild(link);
        list.appendChild(li);
      });
      result.appendChild(list);
    }

    result.appendChild(
      paragraph(`Modèle : ${payload.provider} / ${payload.model}`, "ask-result__technical"),
    );
  };

  const renderError = (message) => {
    clear();
    result.appendChild(paragraph("Erreur", "eyebrow"));
    result.appendChild(paragraph(message, "ask-result__answer"));
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = question.value.trim();
    if (!value) return;

    button.disabled = true;
    button.textContent = "Analyse…";
    result.hidden = false;
    result.replaceChildren(paragraph("Analyse en cours…", "ask-result__loading"));

    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: value }),
      });
      const payload = await response.json();
      if (!response.ok) {
        renderError(payload.message || "La réponse IA a échoué.");
        return;
      }
      renderAnswer(payload);
    } catch (_error) {
      renderError("Impossible de joindre le serveur ACFPF.");
    } finally {
      button.disabled = false;
      button.textContent = "Analyser";
    }
  });
})();
