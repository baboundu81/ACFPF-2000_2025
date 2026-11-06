// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright (C) 2026 ACFPF contributors

// Shared NDJSON transport: progress is immediate, a result is published only after a complete stream.
window.ACFPFConsumeResearchStream = async (response, onEvent) => {
  if (!response.body) throw new Error("Réponse de recherche non diffusable.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const types = new Set(["started", "search", "open", "read", "notice", "answer", "error"]);
  let buffer = "";
  let terminal = null;
  const consumeLine = (line) => {
    if (!line.trim()) return;
    let event;
    try { event = JSON.parse(line); }
    catch (_error) { throw new Error("Le flux de recherche contient une réponse invalide."); }
    if (!event || !types.has(event.type) || terminal) {
      throw new Error("Le flux de recherche est incohérent ou interrompu.");
    }
    if (event.type === "answer" || event.type === "error") {
      if (event.type === "answer" && (!event.answer ||
          !["answered", "insufficient"].includes(event.answer.status) ||
          typeof event.answer.answer !== "string" || !Array.isArray(event.answer.citations))) {
        throw new Error("La réponse finale de recherche est invalide.");
      }
      terminal = event;
    } else onEvent(event);
  };
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      if (buffer.length > 2_000_000) throw new Error("Le flux de recherche dépasse la limite autorisée.");
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) consumeLine(line);
      if (done) break;
    }
    if (buffer.trim()) consumeLine(buffer);
    if (!terminal) throw new Error("La recherche a été interrompue sans réponse finale. Réessayez.");
    if (terminal.type === "error") {
      onEvent(terminal);
      throw new Error(terminal.message || "La recherche a échoué.");
    }
    return terminal.answer;
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
};
