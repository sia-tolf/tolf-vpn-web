const LOCATION_API = "https://location.tolf.is";
const entryPointNote = document.getElementById("entryPointNote");
let recommendedEntryPoint = null;

function renderEntryPointRecommendation() {
  if (!entryPointNote) return;

  const key = recommendedEntryPoint === "moscow"
    ? "entryPointRecommendationMoscow"
    : recommendedEntryPoint === "riga"
      ? "entryPointRecommendationRiga"
      : null;

  if (!key) {
    entryPointNote.textContent = "";
    entryPointNote.classList.add("hidden");
    return;
  }

  entryPointNote.textContent = t(key);
  entryPointNote.classList.remove("hidden");
}

async function loadEntryPointRecommendation() {
  try {
    const response = await fetch(`${LOCATION_API}/recommendation`, {
      method: "GET",
      cache: "no-store",
      credentials: "omit",
      headers: { Accept: "application/json" }
    });

    if (!response.ok) return;

    const data = await response.json();
    if (data.entryPoint !== "moscow" && data.entryPoint !== "riga") return;

    recommendedEntryPoint = data.entryPoint;
    renderEntryPointRecommendation();
  } catch {
    // The recommendation is optional. VPN controls remain available.
  }
}

languageEn.addEventListener("click", renderEntryPointRecommendation);
languageRu.addEventListener("click", renderEntryPointRecommendation);

renderEntryPointRecommendation();
loadEntryPointRecommendation();
