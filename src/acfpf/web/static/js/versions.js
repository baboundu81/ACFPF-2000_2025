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

  async function toggleText(button, panel, version) {
    if (panel.dataset.loaded === "1") {
      panel.hidden = !panel.hidden;
      button.textContent = panel.hidden ? "Afficher le texte officiel" : "Masquer le texte";
      button.setAttribute("aria-expanded", String(!panel.hidden));
      return;
    }
    button.disabled = true;
    button.textContent = "Lecture de la source officielle…";
    panel.hidden = false;
    panel.replaceChildren(node("p", "filter-note", "Récupération du document en cours…"));
    try {
      const url = `${api}/${encodeURIComponent(version.uid)}/text`;
      const response = await fetch(url, { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Document indisponible");
      if (payload.uid !== version.uid || payload.dossier_id !== dossierId) {
        throw new Error("Identité du document incohérente");
      }
      panel.replaceChildren();
      panel.append(node("p", "filter-note",
        "Transcription mécanique du HTML officiel ; la structure juridique des articles et l'exhaustivité des annexes ne sont pas vérifiées."));
      panel.append(node("p", "amendment-row__meta",
        `Consulté le ${payload.retrieved_at} · SHA-256 : ${payload.sha256}`));
      panel.append(node("p", "amendment-detail__text", payload.text));
      const link = node("a", "amendment-detail__source", "Ouvrir le document HTML original");
      link.href = payload.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      panel.append(link);
      panel.dataset.loaded = "1";
      button.textContent = "Masquer le texte";
      button.setAttribute("aria-expanded", "true");
    } catch (error) {
      panel.replaceChildren(node("p", "source-warning",
        `Impossible de vérifier le contenu HTML : ${error.message}. Consultez le dossier officiel.`));
      button.textContent = "Réessayer la lecture";
      button.setAttribute("aria-expanded", "true");
    } finally {
      button.disabled = false;
    }
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
    if (version.notice_available) {
      const actions = node("div", "amendment-row__actions");
      const button = node("button", "amendment-detail-button", "Afficher le texte officiel");
      button.type = "button";
      button.setAttribute("aria-expanded", "false");
      const panel = node("div", "amendment-detail");
      panel.hidden = true;
      button.addEventListener("click", () => toggleText(button, panel, version));
      actions.append(button);
      row.append(actions, panel);
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
