// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright (C) 2026 ACFPF contributors

(() => {
  const form = document.getElementById("ai-settings-form");
  const provider = document.getElementById("ai-provider");
  const model = document.getElementById("ai-model-name");
  const zone = document.getElementById("key-drop-zone");
  const input = document.getElementById("ai-key-file");
  const status = document.getElementById("key-file-status");
  const button = form.querySelector('button[type="submit"]');
  const label = button.textContent;

  function announce(message) {
    status.hidden = !message;
    status.textContent = message;
  }

  function selectionChanged() {
    announce(input.files.length === 1 ? "Fichier sélectionné." : "");
  }

  provider.addEventListener("change", () => {
    model.textContent = provider.selectedOptions[0].dataset.model;
  });
  input.addEventListener("change", selectionChanged);

  zone.addEventListener("dragover", (event) => {
    if (!Array.from(event.dataTransfer.types).includes("Files")) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    zone.classList.add("is-dragging");
  });
  zone.addEventListener("dragleave", (event) => {
    if (!zone.contains(event.relatedTarget)) zone.classList.remove("is-dragging");
  });
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("is-dragging");
    const files = event.dataTransfer.files;
    if (files.length !== 1) {
      input.value = "";
      announce("Déposez un seul fichier contenant la clé.");
      return;
    }
    // Use the browser's normal file field; do not read the credential in JavaScript.
    input.files = files;
    selectionChanged();
  });

  form.addEventListener("submit", () => {
    form.setAttribute("aria-busy", "true");
    button.disabled = true;
    button.textContent = "Activation…";
  });
  window.addEventListener("pageshow", () => {
    form.removeAttribute("aria-busy");
    button.disabled = false;
    button.textContent = label;
    model.textContent = provider.selectedOptions[0].dataset.model;
    selectionChanged();
  });
})();
