// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
(() => {
  const root = document.querySelector("[data-votes-dossier-id]");
  if (!root) return;
  const id = root.dataset.votesDossierId;
  const list = document.getElementById("votes-list");
  const count = document.getElementById("votes-count");
  const status = document.getElementById("votes-status");
  const more = document.getElementById("votes-more");
  if (!id || !list || !count || !status || !more) return;

  const endpoint = `/api/legislation/${encodeURIComponent(id)}/votes`;
  const limit = 20;
  let offset = 0;
  let loading = false;

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = value;
    return node;
  }

  function positionLabel(position) {
    return ({
      pour: "Pour",
      contre: "Contre",
      abstention: "Abstention",
      non_votant: "Non-votant déclaré",
    })[position] || "Position non reconnue";
  }

  function nominalViewer(vote) {
    const wrapper = element("div", "amendment-row__actions");
    const button = element("button", "amendment-detail-button", "Afficher les positions nominatives");
    button.type = "button";
    button.setAttribute("aria-expanded", "false");
    const panel = element("div", "amendment-detail");
    panel.hidden = true;
    const summary = element("p", "filter-note", "");
    const positions = element("div", "amendments-list");
    const morePositions = element("button", "amendments-more", "Afficher d'autres positions");
    morePositions.type = "button";
    morePositions.hidden = true;
    panel.append(
      element("p", "filter-note",
        "Les identités sont recherchées dans l'annuaire officiel historique. Les identifiants restent visibles pour permettre la vérification ; un nom manquant ne signifie pas qu'une personne n'a pas voté."),
      summary, positions, morePositions,
    );
    wrapper.append(button);
    const api = `${endpoint}/${encodeURIComponent(vote.uid)}/positions`;
    const pageSize = 50;
    let shown = 0;
    let total = 0;
    let fetching = false;
    let fetched = false;

    async function loadPositions() {
      if (fetching) return;
      fetching = true;
      button.disabled = true;
      morePositions.disabled = true;
      summary.textContent = "Consultation des positions officielles…";
      const params = new URLSearchParams({
        limit: String(pageSize), offset: String(shown), names: "1",
      });
      try {
        const response = await fetch(`${api}?${params}`, {
          headers: { Accept: "application/json" },
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.message || "Source indisponible");
        if (payload.dossier_id !== id || payload.vote_uid !== vote.uid) {
          throw new Error("Incohérence des références officielles");
        }
        if (!payload.available) {
          summary.textContent = payload.reason || "Aucune liste nominative publiée.";
          morePositions.hidden = true;
          fetched = true;
          return;
        }
        const items = payload.positions || [];
        total = payload.count;
        items.forEach((actor) => {
          const officialIdentity = actor.actor_name
            ? `${actor.actor_name} (${actor.actor_ref})` : actor.actor_ref;
          const line = element("p", "amendment-row__meta",
            `${officialIdentity} · ${positionLabel(actor.position)} · Groupe : ${actor.group_ref}` +
            (actor.by_delegation === true ? " · Par délégation" : ""));
          positions.append(line);
        });
        shown += items.length;
        summary.textContent = `${shown} sur ${total} position(s) nominative(s) publiée(s).` +
          (payload.actor_names_warning ? ` ${payload.actor_names_warning}` : "");
        morePositions.hidden = shown >= total || items.length === 0;
        fetched = true;
      } catch (error) {
        summary.textContent = `Impossible de consulter les positions : ${error.message}`;
        morePositions.hidden = true;
      } finally {
        fetching = false;
        button.disabled = false;
        morePositions.disabled = false;
      }
    }

    button.addEventListener("click", () => {
      panel.hidden = !panel.hidden;
      button.setAttribute("aria-expanded", String(!panel.hidden));
      button.textContent = panel.hidden
        ? "Afficher les positions nominatives" : "Masquer les positions nominatives";
      if (!panel.hidden && !fetched) loadPositions();
    });
    morePositions.addEventListener("click", loadPositions);
    return [wrapper, panel];
  }

  function render(vote) {
    const item = element("article", "amendment-row");
    item.append(element("h3", "amendment-row__number", `Scrutin n° ${vote.number}`));
    item.append(element("p", "amendment-row__meta",
      [vote.date, vote.result].filter(Boolean).join(" · ")));
    item.append(element("p", "filter-note", vote.title || "Objet du scrutin non renseigné"));
    const counts = [
      vote.pour == null ? null : `Pour : ${vote.pour}`,
      vote.contre == null ? null : `Contre : ${vote.contre}`,
      vote.abstentions == null ? null : `Abstentions : ${vote.abstentions}`,
    ].filter(Boolean);
    if (counts.length) item.append(element("p", "amendment-row__meta", counts.join(" · ")));
    const link = element("a", "amendment-detail__source", "Consulter le scrutin à l'Assemblée nationale");
    link.href = vote.official_url;
    link.target = "_blank";
    link.rel = "noreferrer";
    item.append(link);
    item.append(...nominalViewer(vote));
    return item;
  }

  async function load() {
    if (loading) return;
    loading = true;
    more.disabled = true;
    status.textContent = "Chargement des scrutins officiels…";
    try {
      const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
      const response = await fetch(`${endpoint}?${params}`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Source indisponible");
      if (!payload.available) {
        count.textContent = "Scrutins indisponibles";
        status.textContent = payload.reason || "Aucune référence officielle liée";
        more.hidden = true;
        return;
      }
      const votes = payload.votes || [];
      votes.forEach((vote) => list.append(render(vote)));
      offset += votes.length;
      count.textContent = `${payload.count} scrutin(s) rattaché(s)`;
      status.textContent = votes.length
        ? `${offset} sur ${payload.count} scrutin(s) affiché(s).`
        : offset ? "Tous les scrutins rattachés ont été affichés."
          : "Aucun scrutin doté d'un rattachement officiel explicite n'a été trouvé.";
      more.hidden = offset >= payload.count || votes.length === 0;
    } catch (error) {
      status.textContent = `Impossible de charger les scrutins : ${error.message}`;
      more.hidden = true;
    } finally {
      loading = false;
      more.disabled = false;
    }
  }

  more.addEventListener("click", load);
  load();
})();
