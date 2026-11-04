(() => {
  const root = document.querySelector("[data-versions-dossier-id]");
  if (!root) return;

  const dossierId = root.dataset.versionsDossierId;
  const list = document.getElementById("versions-list");
  const count = document.getElementById("versions-count");
  const status = document.getElementById("versions-status");
  const more = document.getElementById("versions-more");
  if (!dossierId || !list || !count || !status || !more) return;

  const api = `/api/legislation/${encodeURIComponent(dossierId)}/versions`;
  const pageSize = 20;
  let offset = 0;
  let busy = false;

  function node(tag, className, text) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
  }

  function render(version) {
    const row = node("article", "amendment-row");
    const heading = node("h3", "amendment-row__number", version.title || version.uid);
    row.append(heading);
    const pieces = [
      version.kind,
      version.provenance,
      version.stage_label,
      version.stage_date || version.publication_date,
    ].filter(Boolean);
    row.append(node("p", "amendment-row__meta", pieces.join(" · ")));
    row.append(node("p", "filter-note", `Référence officielle : ${version.uid}`));
    if (!version.notice_available) {
      row.append(node("p", "filter-note", "Notice individuelle non disponible dans l'archive."));
    }
    const link = node("a", "amendment-detail__source", "Retrouver le document depuis le dossier officiel");
    link.href = version.dossier_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    row.append(link);
    return row;
  }

  async function load() {
    if (busy) return;
    busy = true;
    more.disabled = true;
    status.textContent = "Chargement des références officielles…";
    const query = new URLSearchParams({ offset: String(offset), limit: String(pageSize) });
    try {
      const response = await fetch(`${api}?${query}`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Source indisponible");
      if (!payload.available) {
        count.textContent = "Versions indisponibles";
        status.textContent = payload.reason || "Aucun document Assemblée rattaché.";
        more.hidden = true;
        return;
      }
      const versions = payload.versions || [];
      versions.forEach((item) => list.append(render(item)));
      offset += versions.length;
      count.textContent = `${payload.count} référence(s) de texte`;
      status.textContent = offset
        ? `${offset} sur ${payload.count} référence(s) affichée(s).`
        : "Aucune version documentaire identifiée pour ce dossier.";
      more.hidden = offset >= payload.count || versions.length === 0;
    } catch (error) {
      status.textContent = `Impossible de charger les versions : ${error.message}`;
      more.hidden = true;
    } finally {
      busy = false;
      more.disabled = false;
    }
  }

  more.addEventListener("click", load);
  load();
})();
