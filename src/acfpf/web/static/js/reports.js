// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
(() => {
  const root = document.querySelector("[data-reports-dossier-id]");
  if (!root) return;
  const dossierId = root.dataset.reportsDossierId;
  const list = document.getElementById("reports-list");
  const count = document.getElementById("reports-count");
  const status = document.getElementById("reports-status");
  const more = document.getElementById("reports-more");
  if (!dossierId || !list || !count || !status || !more) return;

  const api = `/api/legislation/${encodeURIComponent(dossierId)}/reports`;
  const pageSize = 20;
  let offset = 0;
  let loading = false;

  function node(tag, cls, text) {
    const item = document.createElement(tag);
    if (cls) item.className = cls;
    if (text !== undefined) item.textContent = text;
    return item;
  }

  async function showText(button, panel, report) {
    if (panel.dataset.loaded === "1") {
      panel.hidden = !panel.hidden;
      button.setAttribute("aria-expanded", String(!panel.hidden));
      button.textContent = panel.hidden ? "Lire le rapport HTML" : "Masquer le rapport";
      return;
    }
    panel.hidden = false;
    button.disabled = true;
    button.textContent = "Ouverture de la source…";
    panel.replaceChildren(node("p", "filter-note", "Lecture du rapport officiel en cours…"));
    try {
      const response = await fetch(`${api}/${encodeURIComponent(report.uid)}/text`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Source indisponible");
      if (payload.uid !== report.uid || payload.dossier_id !== dossierId) {
        throw new Error("Identité officielle du rapport incohérente");
      }
      panel.replaceChildren();
      panel.append(node("p", "filter-note",
        "Transcription mécanique du HTML officiel. Les arguments de ce rapport ne constituent pas du droit en vigueur."));
      panel.append(node("p", "amendment-row__meta",
        `Source consultée le ${payload.retrieved_at} · SHA-256 : ${payload.sha256}`));
      panel.append(node("p", "amendment-detail__text", payload.text));
      const link = node("a", "amendment-detail__source", "Ouvrir le rapport original à l'Assemblée");
      link.href = payload.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      panel.append(link);
      panel.dataset.loaded = "1";
      button.textContent = "Masquer le rapport";
      button.setAttribute("aria-expanded", "true");
    } catch (error) {
      panel.replaceChildren(node("p", "source-warning",
        `Impossible de lire le HTML officiel : ${error.message}. Consultez le dossier source.`));
      button.textContent = "Réessayer la lecture";
      button.setAttribute("aria-expanded", "true");
    } finally {
      button.disabled = false;
    }
  }

  function render(report) {
    const item = node("article", "amendment-row");
    item.append(node("h3", "amendment-row__number", report.title || report.uid));
    item.append(node("p", "amendment-row__meta",
      [report.origin, report.provenance, report.publication_date].filter(Boolean).join(" · ")));
    item.append(node("p", "filter-note", `Référence documentaire officielle : ${report.uid}`));
    const link = node("a", "amendment-detail__source", "Retrouver le rapport depuis le dossier officiel");
    link.href = report.dossier_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    item.append(link);
    if (report.html_lookup_supported) {
      const button = node("button", "amendment-detail-button", "Lire le rapport HTML");
      button.type = "button";
      button.setAttribute("aria-expanded", "false");
      const panel = node("div", "amendment-detail");
      panel.hidden = true;
      button.addEventListener("click", () => showText(button, panel, report));
      item.append(button, panel);
    } else {
      item.append(node("p", "filter-note",
        "URL de document HTML non vérifiée pour cette provenance : utilisez le dossier parlementaire."));
    }
    return item;
  }

  async function load() {
    if (loading) return;
    loading = true;
    more.disabled = true;
    status.textContent = "Consultation des notices officielles…";
    try {
      const query = new URLSearchParams({ offset: String(offset), limit: String(pageSize) });
      const response = await fetch(`${api}?${query}`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Catalogue indisponible");
      if (!payload.available) {
        count.textContent = "Rapports indisponibles";
        status.textContent = payload.reason || "Aucune source parlementaire liée";
        more.hidden = true;
        return;
      }
      const items = payload.reports || [];
      items.forEach((report) => list.append(render(report)));
      offset += items.length;
      count.textContent = `${payload.count} rapport(s) référencé(s)`;
      status.textContent = offset
        ? `${offset} sur ${payload.count} rapport(s) affiché(s).`
        : "Aucune notice de rapport directement reliée à ce dossier.";
      more.hidden = offset >= payload.count || items.length === 0;
    } catch (error) {
      status.textContent = `Rapports indisponibles : ${error.message}`;
      more.hidden = true;
    } finally {
      loading = false;
      more.disabled = false;
    }
  }

  more.addEventListener("click", load);
  load();
})();
