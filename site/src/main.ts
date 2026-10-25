// Entry point: hash routing (#/ and #/player/<id>), like a tiny Shiny router.

import "./style.css";
import { renderHome } from "./pages/home";
import { renderPlayer } from "./pages/player";

const app = document.querySelector<HTMLElement>("#app")!;

const go = (id: number) => {
  location.hash = `#/player/${id}`;
};

async function route(): Promise<void> {
  const match = location.hash.match(/^#\/player\/(\d+)/);
  try {
    if (match) await renderPlayer(app, Number(match[1]), go);
    else await renderHome(app, go);
  } catch (err) {
    console.error(err);
    app.innerHTML = `<h1 tabindex="-1">Something went wrong</h1><p>The data could not be loaded. Please reload the page.</p>`;
  }
  window.scrollTo(0, 0);
  // Move focus to the new page's heading so screen readers announce it
  app.querySelector<HTMLElement>("h1")?.focus();
}

window.addEventListener("hashchange", route);
route();

// The skip link moves focus without changing the URL hash (which is used for routing)
document.querySelector(".skip-link")?.addEventListener("click", (e) => {
  e.preventDefault();
  app.focus();
});
