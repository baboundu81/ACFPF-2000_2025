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
