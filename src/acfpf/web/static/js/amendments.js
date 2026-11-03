(() => {
  const root = document.querySelector("[data-amendments-dossier-id]");
  if (!root) return;

  const dossierId = root.dataset.amendmentsDossierId;
  const list = document.getElementById("amendments-list");
  const count = document.getElementById("amendments-count");
  const status = document.getElementById("amendments-status");
  const fateSelect = document.getElementById("amendments-fate");
  const moreButton = document.getElementById("amendments-more");
  if (!dossierId || !list || !count || !status || !fateSelect || !moreButton) return;

  const pageSize = 20;
  let offset = 0;
  let loading = false;
  let filteredCount = 0;

  const apiBase = `/api/legislation/${encodeURIComponent(dossierId)}/amendments`;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function amendmentMeta(item) {
    const values = [item.fate_label, item.instance, item.article, item.author].filter(Boolean);
    return values.join(" · ");
  }

  async function loadDetail(button, panel, amendmentId) {
    if (!panel.hidden) {
      panel.hidden = true;
      button.textContent = "Voir le détail";
      return;
    }
    if (panel.dataset.loaded === "1") {
      panel.hidden = false;
      button.textContent = "Masquer le détail";
      return;
    }

    button.disabled = true;
    button.textContent = "Chargement…";
    try {
      const response = await fetch(`${apiBase}/${encodeURIComponent(amendmentId)}`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Détail indisponible");

      panel.replaceChildren();
      if (payload.dispositif) {
        panel.append(element("h4", "amendment-detail__title", "Dispositif"));
        panel.append(element("p", "amendment-detail__text", payload.dispositif));
      }
      if (payload.purpose) {
        panel.append(element("h4", "amendment-detail__title", "Exposé des motifs"));
        panel.append(element("p", "amendment-detail__text", payload.purpose));
      }
      if (!payload.dispositif && !payload.purpose) {
        panel.append(element("p", "filter-note", "Le détail textuel n'est pas renseigné dans la source structurée."));
      }
      const source = element("a", "amendment-detail__source", "Voir l'amendement officiel");
      source.href = payload.official_url;
      source.target = "_blank";
      source.rel = "noreferrer";
      panel.append(source);
      panel.dataset.loaded = "1";
      panel.hidden = false;
      button.textContent = "Masquer le détail";
    } catch (error) {
      panel.replaceChildren(element("p", "source-warning", `Détail indisponible : ${error.message}`));
      panel.hidden = false;
      button.textContent = "Réessayer";
    } finally {
      button.disabled = false;
    }
  }

  function renderAmendment(item) {
    const article = element("article", "amendment-row");
    const header = element("div", "amendment-row__header");
    header.append(element("strong", "amendment-row__number", `Amendement ${item.number}`));
    header.append(element("span", `amendment-fate amendment-fate--${item.fate}`, item.fate_label));
    article.append(header);

    const meta = amendmentMeta(item);
    if (meta) article.append(element("p", "amendment-row__meta", meta));

    const actions = element("div", "amendment-row__actions");
    const detailButton = element("button", "amendment-detail-button", "Voir le détail");
    detailButton.type = "button";
    const official = element("a", "", "Source officielle");
    official.href = item.official_url;
    official.target = "_blank";
    official.rel = "noreferrer";
    actions.append(detailButton, official);
    article.append(actions);

    const detailPanel = element("div", "amendment-detail");
    detailPanel.hidden = true;
    article.append(detailPanel);
    detailButton.addEventListener("click", () => loadDetail(detailButton, detailPanel, item.id));
    return article;
  }

  async function loadPage({ reset = false } = {}) {
    if (loading) return;
    loading = true;
    moreButton.disabled = true;
    status.textContent = "Chargement des amendements…";
    if (reset) {
      offset = 0;
      filteredCount = 0;
      list.replaceChildren();
      moreButton.hidden = true;
    }

    const params = new URLSearchParams({
      offset: String(offset),
      limit: String(pageSize),
    });
    if (fateSelect.value) params.set("fate", fateSelect.value);

    try {
      const response = await fetch(`${apiBase}?${params.toString()}`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Index indisponible");

      if (!payload.available) {
        count.textContent = "Amendements structurés indisponibles";
        status.textContent = payload.reason || "Aucune source structurée disponible pour ce dossier.";
        list.replaceChildren();
        moreButton.hidden = true;
        return;
      }

      filteredCount = payload.filtered_count;
      count.textContent = `${payload.filtered_count} amendement(s) correspondant(s) sur ${payload.count}`;
      payload.amendments.forEach((item) => list.append(renderAmendment(item)));
      offset += payload.amendments.length;
      moreButton.hidden = offset >= filteredCount;
      status.textContent = payload.amendments.length
        ? `${offset} sur ${filteredCount} affiché(s).`
        : "Aucun amendement ne correspond à ce filtre.";
    } catch (error) {
      status.textContent = `Impossible de charger les amendements : ${error.message}`;
      if (reset) list.replaceChildren();
      moreButton.hidden = true;
    } finally {
      loading = false;
      moreButton.disabled = false;
    }
  }

  fateSelect.addEventListener("change", () => loadPage({ reset: true }));
  moreButton.addEventListener("click", () => loadPage());
  loadPage({ reset: true });
})();
