// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright (C) 2026 ACFPF contributors
(() => {
  document.querySelectorAll(".legislation-search, .legislation-filters").forEach((form) => {
    const button = form.querySelector("button[type='submit']");
    if (!button) return;
    const label = button.textContent;
    form.addEventListener("submit", () => {
      form.setAttribute("aria-busy", "true");
      button.disabled = true;
      button.textContent = "Recherche des dossiers…";
    });
    window.addEventListener("pageshow", () => {
      form.setAttribute("aria-busy", "false");
      button.disabled = false;
      button.textContent = label;
    });
  });
})();
