// About page: data source, attribution, terms, reproducibility.

const REPO = "https://github.com/kang6002/hot-hand";

export function renderAbout(app: HTMLElement): void {
  document.title = "About · Is the Hot Hand Real?";
  app.innerHTML = `
    <h1 tabindex="-1">About</h1>
    <p class="lede">A student project that tests, player by player, whether NBA shooting streaks are distinguishable
      from luck, with honest effect sizes and uncertainty.</p>

    <h2>Data</h2>
    <p>Every regular-season field-goal attempt since 1996-97 (when shot-level data begins), downloaded from NBA.com Stats
      with the open-source <a href="https://github.com/swar/nba_api">nba_api</a> Python package: who shot, in which game,
      when, from where, and whether it went in.</p>
    <p><strong>Data: NBA.com Stats via nba_api. Not affiliated with or endorsed by the NBA.</strong> The data belongs to the
      NBA and is used here for personal, non-commercial purposes under the NBA.com terms of use. This site publishes only
      derived statistics, not the raw data.</p>

    <h2>How it's built</h2>
    <ul>
      <li>A Python pipeline (pandas, NumPy, SciPy, statsmodels) downloads, cleans and analyses the shots, with automated
        tests that check the statistics on simulated players.</li>
      <li>The results are written as small static files; this website (TypeScript and Observable Plot) reads them in
        your browser. There is no server and no tracking.</li>
      <li>Every decision, with the reasons and alternatives considered, is logged in the project's
        <a href="${REPO}/blob/main/DECISIONS.md">decisions log</a>.</li>
    </ul>

    <h2>Reproduce it</h2>
    <p>All code is on GitHub: <a href="${REPO}">${REPO.replace("https://", "")}</a>. The README explains how to download
      the data and rerun every step on your own computer.</p>

    <h2>Read more</h2>
    <p>See <a href="#/method">how the test works</a> for the statistics, the limitations and the references.</p>`;
}
