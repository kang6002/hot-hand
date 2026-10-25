// Entry point: hash routing (#/, #/league, #/method, #/about, #/player/<id>), like a tiny Shiny router.

import "./style.css";
import { renderAbout } from "./pages/about";
import { renderHome } from "./pages/home";
import { renderLeague } from "./pages/league";
import { renderMethod } from "./pages/method";
import { renderPlayer } from "./pages/player";

const app = document.querySelector<HTMLElement>("#app")!;

const go = (id: number) => {
  location.hash = `#/player/${id}`;
};

async function route(): Promise<void> {
  const match = location.hash.match(/^#\/player\/(\d+)/);
  const page = match ? "player" : (location.hash.match(/^#\/(league|method|about)/)?.[1] ?? "home");
  // Mark the current page in the navigation
  document.querySelectorAll<HTMLAnchorElement>("nav a").forEach((a) => {
    if (a.dataset.route === page) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  try {
    if (match) await renderPlayer(app, Number(match[1]), go);
    else if (page === "league") await renderLeague(app, go);
    else if (page === "method") await renderMethod(app);
    else if (page === "about") renderAbout(app);
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
