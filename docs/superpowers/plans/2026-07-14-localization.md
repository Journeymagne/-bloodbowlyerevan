# EN/RU Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live EN/RU language switcher to the Gata Blood Bowl League site that translates all interface chrome and all reference content, while keeping Blood Bowl proper nouns and keywords in English in both locales.

**Architecture:** Two independent i18n layers sharing one `state.locale`: (1) a `src/i18n/{en,ru}.json` dictionary + `t()` helper for interface strings in `index.html`/`src/app.js`; (2) a parallel Markdown vault `content/Gata-ru/` mirroring `content/Gata/`'s file/folder structure, built into `public/data.ru.json` alongside the existing `public/data.en.json` by an extended `scripts/build-data.mjs`. Switching locale re-fetches the matching `data.<locale>.json` (cached after first load) and re-runs the existing hash-router's `renderRoute()` — no page reload.

**Tech Stack:** Vanilla JS (no framework, no bundler), Node.js build scripts (`.mjs`, ESM), static JSON as the data interchange format. No test framework exists in this repo; verification is manual (`npm run dev` + browser) plus one small Node verification script introduced in Task 7.

**Design reference:** `docs/superpowers/specs/2026-07-14-localization-design.md`

## Global Constraints

- Team/race names, skill/trait names, player positions, star player names, inducement/special-rule names, and core stat shorthand (MA/ST/AG/PA/AV/SPP/TV/GP/CAS) stay in English in **both** locales, in UI strings and in translated content.
- `content/Gata-ru/` mirrors `content/Gata/`'s directory and file names exactly — never rename or reorganize files when translating.
- `content/7ZBBL/` (a separate, unrelated league's Russian content) is out of scope. Never edit it.
- Locale switching is instant and client-side: no `location.reload()`, no hash change, current route/filters/scroll are preserved.
- Locale persistence key: `localStorage["gata-league-locale"]`. Default for a visitor with no saved preference: `ru` if any of `navigator.languages` starts with `ru`, else `en`.
- `public/data.json` must keep being written (as a byte-for-byte copy of the `en` build) for backward compatibility with anything still pointing at the old filename.
- No automated test suite exists in this repo — do not introduce one. Verification is: run `npm run dev`, exercise the change in a browser, and (for content tasks) run the verification script from Task 7.

---

### Task 1: Build pipeline — dual-locale `data.json` output

**Files:**
- Modify: `scripts/build-data.mjs:1-8` (top-level constants)
- Modify: `scripts/build-data.mjs:566-608` (`extractTeamMeta`, `extractStarPlayerMeta` — fix broken Cyrillic label regexes)
- Modify: `scripts/build-data.mjs:637-758` (wrap the build body in a reusable function, call it twice)

**Interfaces:**
- Produces: `public/data.en.json`, `public/data.ru.json`, `public/data.json` (alias of `data.en.json`). Consumed by Task 2's frontend loader (`fetch("public/data.<locale>.json")`).
- Produces: corrected bold-label parsing so `content/Gata-ru` team/star-player files can use the Russian labels `**Перебросы:**`, `**Апотекарий:**`, `**Лига:**`, `**Специальные правила:**`, `**Доступность:**`, `**Цена:**`, `**Команды:**` and still populate `page.team.meta` / `page.starPlayer` correctly. Consumed by Tasks 13 and 14 (Star Players and Teams translation).

- [ ] **Step 1: Read the current top of the file to confirm line numbers still match**

Run: `sed -n '1,10p' scripts/build-data.mjs`
Expected output:
```js
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const vaultDir = path.join(rootDir, "content", process.env.SITE_CONTENT_DIR || "Gata");
const publicDir = path.join(rootDir, "public");
const dataPath = path.join(publicDir, "data.json");
```

- [ ] **Step 2: Replace the top-level constants**

Replace:
```js
const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const vaultDir = path.join(rootDir, "content", process.env.SITE_CONTENT_DIR || "Gata");
const publicDir = path.join(rootDir, "public");
const dataPath = path.join(publicDir, "data.json");
```
With:
```js
const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const primaryContentDir = process.env.SITE_CONTENT_DIR || "Gata";
const vaultDir = path.join(rootDir, "content", primaryContentDir);
const ruVaultDir = path.join(rootDir, "content", `${primaryContentDir}-ru`);
const publicDir = path.join(rootDir, "public");
```

- [ ] **Step 3: Fix the broken Cyrillic label patterns in `extractTeamMeta`**

The existing Cyrillic branches in this function are mojibake (double-encoded bytes) and never match real Cyrillic text — they're silently dead code today. Replace them with the labels actually used by Russian league content (confirmed against `content/7ZBBL/Команды/Amazon.md`).

Replace:
```js
function extractTeamMeta(markdown) {
  const meta = {};
  const patterns = [
    ["rerolls", /\*\*Rerolls:\*\*\s*([^\n]+)/i],
    ["apothecary", /\*\*Apothecary:\*\*\s*([^\n]+)/i],
    ["league", /\*\*League:\*\*\s*([^\n]+)/i],
    ["specialRules", /\*\*Special Rules:\*\*\s*([^\n]+)/i],
    ["rerolls", /\*\*РџРµСЂРµР±СЂРѕСЃС‹:\*\*\s*([^\n]+)/i],
    ["apothecary", /\*\*РђРїРѕС‚РµРєР°СЂРёР№:\*\*\s*([^\n]+)/i],
    ["league", /\*\*Р›РёРіР°:\*\*\s*([^\n]+)/i],
    ["specialRules", /\*\*РЎРїРµС†РёР°Р»СЊРЅС‹Рµ РїСЂР°РІРёР»Р°:\*\*\s*([^\n]+)/i],
  ];
```
With:
```js
function extractTeamMeta(markdown) {
  const meta = {};
  const patterns = [
    ["rerolls", /\*\*Rerolls:\*\*\s*([^\n]+)/i],
    ["apothecary", /\*\*Apothecary:\*\*\s*([^\n]+)/i],
    ["league", /\*\*League:\*\*\s*([^\n]+)/i],
    ["specialRules", /\*\*Special Rules:\*\*\s*([^\n]+)/i],
    ["rerolls", /\*\*Перебросы:\*\*\s*([^\n]+)/i],
    ["apothecary", /\*\*Апотекарий:\*\*\s*([^\n]+)/i],
    ["league", /\*\*Лига:\*\*\s*([^\n]+)/i],
    ["specialRules", /\*\*Специальные правила:\*\*\s*([^\n]+)/i],
  ];
```

(Leave the rest of the function — the `for` loop and `return meta;` — untouched.)

- [ ] **Step 4: Fix the broken Cyrillic label patterns in `extractStarPlayerMeta`**

Replace:
```js
function extractStarPlayerMeta(markdown) {
  const meta = {};
  const patterns = [
    ["availability", /\*\*Availability:\*\*\s*([^\n]+)/i],
    ["cost", /\*\*Cost:\*\*\s*([^\n]+)/i],
    ["teams", /\*\*Teams:\*\*\s*([^\n]+)/i],
    ["availability", /\*\*Р”РѕСЃС‚СѓРїРЅРѕСЃС‚СЊ:\*\*\s*([^\n]+)/i],
    ["cost", /\*\*Р¦РµРЅР°:\*\*\s*([^\n]+)/i],
    ["teams", /\*\*РљРѕРјР°РЅРґС‹:\*\*\s*([^\n]+)/i],
  ];
```
With:
```js
function extractStarPlayerMeta(markdown) {
  const meta = {};
  const patterns = [
    ["availability", /\*\*Availability:\*\*\s*([^\n]+)/i],
    ["cost", /\*\*Cost:\*\*\s*([^\n]+)/i],
    ["teams", /\*\*Teams:\*\*\s*([^\n]+)/i],
    ["availability", /\*\*Доступность:\*\*\s*([^\n]+)/i],
    ["cost", /\*\*Цена:\*\*\s*([^\n]+)/i],
    ["teams", /\*\*Команды:\*\*\s*([^\n]+)/i],
  ];
```

(Leave the rest of the function untouched. Note as a side effect: this also fixes metadata parsing for the pre-existing `content/7ZBBL` vault, which was silently broken the same way — that vault is otherwise untouched by this plan.)

- [ ] **Step 5: Wrap the build body in a `buildLocaleData(sourceDir)` function**

Find the block starting at `const files = await walk(vaultDir);` (currently line 637) and ending at the `otherPages` assignment (currently line 725) — this is the per-vault page-building logic. Change its two references to the outer `vaultDir` into a `sourceDir` parameter, and wrap it in a function.

Replace:
```js
const files = await walk(vaultDir);
const rawPages = [];

for (const file of files) {
  const relativePath = path.relative(vaultDir, file);
```
With:
```js
async function buildLocaleData(sourceDir) {
const files = await walk(sourceDir);
const rawPages = [];

for (const file of files) {
  const relativePath = path.relative(sourceDir, file);
```

- [ ] **Step 6: Close the new function after the `data` object is built, and replace the final write with a two-locale build**

Find the tail of the file:
```js
const data = {
  generatedAt: new Date().toISOString(),
  counts: {
    pages: pages.length,
    teams: teams.length,
    skills: skills.length,
    traits: traits.length,
    rules: rules.length,
    cheatsheets: cheatsheets.length,
    inducements: inducements.length,
    starPlayers: starPlayers.length,
  },
  unresolvedLinks: [...new Set(
    pages.flatMap((page) => [...page.body.matchAll(/\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]/g)]
      .map((match) => match[1].trim())
      .filter((target) => !resolveLinkedPage(pageByTitle, target) && !virtualLinks.has(target)))
  )],
  skillGroups: parseSkillGroups(pages),
  pages,
  teams,
  skills,
  traits,
  rules,
  cheatsheets,
  inducements,
  starPlayers,
  otherPages,
};

await fs.mkdir(publicDir, { recursive: true });
await fs.writeFile(dataPath, JSON.stringify(data, null, 2), "utf8");

console.log(`Built ${data.counts.pages} pages into ${path.relative(rootDir, dataPath)}`);
```
Replace it with:
```js
const data = {
  generatedAt: new Date().toISOString(),
  counts: {
    pages: pages.length,
    teams: teams.length,
    skills: skills.length,
    traits: traits.length,
    rules: rules.length,
    cheatsheets: cheatsheets.length,
    inducements: inducements.length,
    starPlayers: starPlayers.length,
  },
  unresolvedLinks: [...new Set(
    pages.flatMap((page) => [...page.body.matchAll(/\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]/g)]
      .map((match) => match[1].trim())
      .filter((target) => !resolveLinkedPage(pageByTitle, target) && !virtualLinks.has(target)))
  )],
  skillGroups: parseSkillGroups(pages),
  pages,
  teams,
  skills,
  traits,
  rules,
  cheatsheets,
  inducements,
  starPlayers,
  otherPages,
};

return data;
}

await fs.mkdir(publicDir, { recursive: true });

const enData = await buildLocaleData(vaultDir);
await fs.writeFile(path.join(publicDir, "data.en.json"), JSON.stringify(enData, null, 2), "utf8");
await fs.writeFile(path.join(publicDir, "data.json"), JSON.stringify(enData, null, 2), "utf8");
console.log(`Built ${enData.counts.pages} pages into public/data.en.json (+ data.json alias)`);

let ruSourceDir = ruVaultDir;
try {
  await fs.access(ruVaultDir);
} catch {
  console.warn(`content/${primaryContentDir}-ru not found yet; using ${primaryContentDir} content for public/data.ru.json`);
  ruSourceDir = vaultDir;
}
const ruData = await buildLocaleData(ruSourceDir);
await fs.writeFile(path.join(publicDir, "data.ru.json"), JSON.stringify(ruData, null, 2), "utf8");
console.log(`Built ${ruData.counts.pages} pages into public/data.ru.json`);
```

- [ ] **Step 7: Run the build and verify both files are produced**

Run: `npm run build`
Expected output includes both:
```
Built 299 pages into public/data.en.json (+ data.json alias)
content/Gata-ru not found yet; using Gata content for public/data.ru.json
Built 299 pages into public/data.ru.json
```
(Page count will match whatever `content/Gata` currently has — verify it's a positive, non-zero number, and that `public/data.en.json`, `public/data.ru.json`, and `public/data.json` all exist: `ls -la public/*.json`.)

- [ ] **Step 8: Confirm `data.ru.json` and `data.en.json` are byte-identical at this point**

Run: `diff public/data.en.json public/data.ru.json && echo IDENTICAL`
Expected: `IDENTICAL` (they must be identical now, since `content/Gata-ru` doesn't exist yet — this diff will start showing differences only after Task 8 onward creates translated content).

- [ ] **Step 9: Commit**

```bash
git add scripts/build-data.mjs
git commit -m "Build data.en.json and data.ru.json from separate content vaults"
```

---

### Task 2: Frontend i18n core — locale state, `t()` helper, live language toggle

**Files:**
- Create: `src/i18n/en.json`
- Create: `src/i18n/ru.json`
- Modify: `src/app.js:1-55` (state object)
- Modify: `src/app.js:57-89` (module-level DOM refs / storage keys)
- Modify: `src/app.js:3787-3852` (`init()`, bootstrap, error fallback)
- Modify: `index.html:2` (`<html lang="en">` becomes dynamically managed)

**Interfaces:**
- Produces: `t(key)` — global helper, returns the active locale's string for `key`, falling back to English, falling back to the raw key. Used by every task from here on.
- Produces: `applyStaticI18n()` — walks `[data-i18n]`/`[data-i18n-placeholder]`/`[data-i18n-title]`/`[data-i18n-aria-label]` elements and fills them from `t()`. Used by Task 3.
- Produces: `switchLocale(nextLocale)` — updates `state.locale`, persists it, reloads `state.data` for that locale, re-applies chrome, calls `renderRoute()`.
- Produces: `state.locale` (`"en"` or `"ru"`) — read by every render function from Task 4 onward via `t()`; render functions never read `state.locale` directly.
- Consumes: `renderRoute()` (existing, `src/app.js:3771`) — called after every locale switch.

- [ ] **Step 1: Create the English UI dictionary**

Create `src/i18n/en.json`:
```json
{
  "lang.toggleTitle": "Switch to Russian",
  "footer.updated": "Updated",
  "app.dataLoadError": "Could not load site data."
}
```

- [ ] **Step 2: Create the Russian UI dictionary**

Create `src/i18n/ru.json`:
```json
{
  "lang.toggleTitle": "Переключить на английский",
  "footer.updated": "Обновлено",
  "app.dataLoadError": "Не удалось загрузить данные сайта."
}
```

- [ ] **Step 3: Add `locale` to `state` and add locale/translation module-level constants**

In `src/app.js`, find the `state` object (currently lines 1-55) and add a `locale` field. Replace:
```js
const state = {
  data: null,
  query: "",
```
With:
```js
const state = {
  data: null,
  locale: "en",
  query: "",
```

Then find the storage-key constants block (currently lines 78-89):
```js
const authTokenKey = "gata-league-auth-token";
const themeStorageKey = "gata-league-theme";
```
Add directly below it:
```js
const localeStorageKey = "gata-league-locale";
const supportedLocales = new Set(["en", "ru"]);
const dataCache = new Map();
let translations = { en: {}, ru: {} };
let activeDict = translations.en;
```

- [ ] **Step 4: Add the locale-detection, translation-loading, and `t()`/`applyStaticI18n()` functions**

Directly below `applyTheme` (currently ends at `src/app.js:125`), add:
```js
function detectDefaultLocale() {
  const languages = navigator.languages && navigator.languages.length
    ? navigator.languages
    : [navigator.language || "en"];
  return languages.some((lang) => lang.toLowerCase().startsWith("ru")) ? "ru" : "en";
}

function storedLocale() {
  try {
    const saved = localStorage.getItem(localeStorageKey);
    return supportedLocales.has(saved) ? saved : detectDefaultLocale();
  } catch (_error) {
    return detectDefaultLocale();
  }
}

async function loadTranslations() {
  const [en, ru] = await Promise.all([
    fetch("src/i18n/en.json", { cache: "no-store" }).then((response) => response.json()),
    fetch("src/i18n/ru.json", { cache: "no-store" }).then((response) => response.json()),
  ]);
  translations = { en, ru };
}

function t(key) {
  return activeDict[key] ?? translations.en[key] ?? key;
}

function applyStaticI18n() {
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.setAttribute("placeholder", t(element.dataset.i18nPlaceholder));
  });
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.setAttribute("title", t(element.dataset.i18nTitle));
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  });
}

async function loadLocaleData(locale) {
  if (dataCache.has(locale)) return dataCache.get(locale);
  let data;
  if (window.__REFERENCE_DATA__ && window.__REFERENCE_DATA__[locale]) {
    data = window.__REFERENCE_DATA__[locale];
  } else {
    const response = await fetch(`public/data.${locale}.json`, { cache: "no-store" });
    data = await response.json();
  }
  dataCache.set(locale, data);
  return data;
}

function applyLocaleChrome() {
  document.documentElement.lang = state.locale;
  activeDict = translations[state.locale];
  applyStaticI18n();
  if (langToggle) {
    langToggle.textContent = state.locale === "en" ? "RU" : "EN";
    langToggle.title = t("lang.toggleTitle");
  }
  if (generatedAt && state.data) {
    const dateLocale = state.locale === "ru" ? "ru-RU" : "en-GB";
    generatedAt.textContent = `${t("footer.updated")} ${new Date(state.data.generatedAt).toLocaleDateString(dateLocale)}`;
  }
}

async function switchLocale(nextLocale) {
  if (!supportedLocales.has(nextLocale) || nextLocale === state.locale) return;
  state.locale = nextLocale;
  try {
    localStorage.setItem(localeStorageKey, nextLocale);
  } catch (_error) {
    // Locale persistence is optional; the switch still works for this session.
  }
  state.data = await loadLocaleData(nextLocale);
  applyLocaleChrome();
  renderRoute();
}
```

- [ ] **Step 5: Rewire `init()` to use locale-aware data loading and chrome**

Find `init()` (currently `src/app.js:3787-3847`). Replace:
```js
async function init() {
  applyTheme(storedTheme(), false);
  if (window.__REFERENCE_DATA__) {
    state.data = window.__REFERENCE_DATA__;
  } else {
    const response = await fetch("public/data.json", { cache: "no-store" });
    state.data = await response.json();
  }
  await loadAuthSession();
  if (generatedAt) {
    generatedAt.textContent = `Updated ${new Date(state.data.generatedAt).toLocaleDateString("en-GB")}`;
  }
```
With:
```js
async function init() {
  applyTheme(storedTheme(), false);
  state.locale = storedLocale();
  await loadTranslations();
  state.data = await loadLocaleData(state.locale);
  await loadAuthSession();
  applyLocaleChrome();
```

- [ ] **Step 6: Wire the toggle button's click handler and remove the old static label block**

Find, inside `init()`:
```js
  if (langToggle) {
    langToggle.textContent = "EN";
    langToggle.title = "English version";
  }
  window.addEventListener("hashchange", renderRoute);
```
Replace with:
```js
  langToggle?.addEventListener("click", () => {
    switchLocale(state.locale === "en" ? "ru" : "en");
  });
  window.addEventListener("hashchange", renderRoute);
```

- [ ] **Step 7: Translate the data-load error fallback and enable the toggle button**

Find, at the bottom of the file:
```js
init().catch((error) => {
  console.error(error);
  view.innerHTML = `<div class="empty-state">Could not load site data.</div>`;
```
Replace with:
```js
init().catch((error) => {
  console.error(error);
  view.innerHTML = `<div class="empty-state">${t("app.dataLoadError")}</div>`;
```

- [ ] **Step 8: Remove the `disabled` attribute from the toggle button in the static markup**

In `index.html`, find:
```html
            <button id="lang-toggle" class="icon-text-button" type="button" disabled title="English version">EN</button>
```
Replace with:
```html
            <button id="lang-toggle" class="icon-text-button" type="button" title="Switch to Russian">EN</button>
```
(This static `title`/text is just the pre-JS placeholder shown for an instant before `init()` runs; `applyLocaleChrome()` overwrites both immediately.)

- [ ] **Step 9: Manually verify the mechanism end-to-end**

Run: `npm run dev`, open `http://localhost:5173` in a browser.
1. Open DevTools → Application → Local Storage, confirm no `gata-league-locale` key yet, confirm the page loaded in English (`EN` toggle unlikely to show `RU`... actually it depends on browser language; if your browser's language is Russian, the site should load in Russian by default — check the toggle shows `EN` in that case).
2. Click `#lang-toggle`. Confirm: the button's label flips (`EN`⇄`RU`), the "Updated ..." dateline's leading word flips between "Updated"/"Обновлено", and the current route (check the URL hash) is unchanged.
3. Open DevTools → Network, filter by "data.". Confirm clicking the toggle fetches `data.ru.json` (or `data.en.json`) exactly once per locale, and does **not** trigger a full page navigation (no `index.html` reload in the Network log).
4. Reload the page. Confirm the site now loads directly in whichever locale you last selected (localStorage persisted it).

- [ ] **Step 10: Commit**

```bash
git add src/i18n/en.json src/i18n/ru.json src/app.js index.html
git commit -m "Add locale state, t() helper, and live EN/RU language toggle"
```

---

### Task 3: Translate the static shell — sidebar, topbar, auth modal

**Files:**
- Modify: `index.html` (sidebar nav, topbar, auth modal — the whole static shell)
- Modify: `src/app.js:234-341` (`setAuthError`, `updateAuthButton`, `setAuthMode` — dynamic auth-modal text)
- Modify: `src/i18n/en.json`, `src/i18n/ru.json` (add all keys introduced by this task)

**Interfaces:**
- Consumes: `t(key)`, `applyStaticI18n()` from Task 2.
- Produces: nothing new consumed by later tasks — this task is a leaf, but establishes the `data-i18n*` convention every later static-markup change should follow.

- [ ] **Step 1: Add `data-i18n` attributes to the sidebar/topbar static markup**

In `index.html`, replace the `<nav class="nav-list">...</nav>` through the topbar's `<div class="top-actions">` block:
```html
        <nav class="nav-list">
          <a href="#/" data-nav="home">Overview</a>
          <a href="#/pages" data-nav="pages">References</a>
          <a href="#/inducements" data-nav="inducements">Inducements</a>
          <a href="#/skills" data-nav="skills">Skills</a>
          <a href="#/traits" data-nav="traits">Traits</a>
          <a href="#/star-players" data-nav="star-players">Star Players</a>
          <a href="#/teams" data-nav="teams">Team's Rules</a>
          <a href="#/builder" data-nav="builder">Team Builder</a>
          <a href="#/my-teams" data-nav="my-teams">My Teams</a>
        </nav>

        <div class="sidebar-footer">
          <span id="generated-at">Loading data</span>
          <p class="legal-note">
            Unofficial fan-made league reference.
            <a href="#/legal" data-nav="legal">Legal Information</a>
          </p>
        </div>
```
With:
```html
        <nav class="nav-list">
          <a href="#/" data-nav="home" data-i18n="nav.overview">Overview</a>
          <a href="#/pages" data-nav="pages" data-i18n="nav.references">References</a>
          <a href="#/inducements" data-nav="inducements" data-i18n="nav.inducements">Inducements</a>
          <a href="#/skills" data-nav="skills" data-i18n="nav.skills">Skills</a>
          <a href="#/traits" data-nav="traits" data-i18n="nav.traits">Traits</a>
          <a href="#/star-players" data-nav="star-players" data-i18n="nav.starPlayers">Star Players</a>
          <a href="#/teams" data-nav="teams" data-i18n="nav.teamsRules">Team's Rules</a>
          <a href="#/builder" data-nav="builder" data-i18n="nav.builder">Team Builder</a>
          <a href="#/my-teams" data-nav="my-teams" data-i18n="nav.myTeams">My Teams</a>
        </nav>

        <div class="sidebar-footer">
          <span id="generated-at" data-i18n="footer.loadingData">Loading data</span>
          <p class="legal-note">
            <span data-i18n="footer.unofficialNote">Unofficial fan-made league reference.</span>
            <a href="#/legal" data-nav="legal" data-i18n="footer.legalLink">Legal Information</a>
          </p>
        </div>
```

Note: `#generated-at`'s `data-i18n="footer.loadingData"` only matters before `init()` finishes; `applyLocaleChrome()` (Task 2, Step 4) overwrites its `textContent` afterward with the dateline, so this key is only ever briefly visible.

- [ ] **Step 2: Add `data-i18n*` to the topbar search input, theme picker, and auth button**

Replace:
```html
        <header class="topbar">
          <button id="nav-toggle" class="nav-toggle" type="button" aria-label="Open menu" aria-controls="site-sidebar" aria-expanded="false">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="M4 7h16M4 12h16M4 17h16"></path>
            </svg>
          </button>
          <div class="search-wrap">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="m21 21-4.3-4.3m1.3-5.2a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0Z"></path>
            </svg>
            <input id="global-search" type="search" placeholder="Search teams, skills, rules..." autocomplete="off">
          </div>
          <div class="top-actions">
            <label class="theme-picker" title="Theme">
              <span>Theme</span>
              <select id="theme-select" aria-label="Theme">
                <option value="dark-gata">Gata Dark</option>
                <option value="dark-dugout">Dugout Dark</option>
                <option value="dark-warpstone">Warpstone Dark</option>
                <option value="light-parchment">Parchment Light</option>
                <option value="light-sideline">Sideline Light</option>
                <option value="light-altdorf">Altdorf Light</option>
              </select>
            </label>
            <button id="auth-button" class="icon-text-button auth-button" type="button">Login</button>
            <button id="lang-toggle" class="icon-text-button" type="button" title="Switch to Russian">EN</button>
          </div>
        </header>
```
With:
```html
        <header class="topbar">
          <button id="nav-toggle" class="nav-toggle" type="button" aria-label="Open menu" data-i18n-aria-label="nav.openMenu" aria-controls="site-sidebar" aria-expanded="false">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="M4 7h16M4 12h16M4 17h16"></path>
            </svg>
          </button>
          <div class="search-wrap">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="m21 21-4.3-4.3m1.3-5.2a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0Z"></path>
            </svg>
            <input id="global-search" type="search" placeholder="Search teams, skills, rules..." data-i18n-placeholder="search.placeholder" autocomplete="off">
          </div>
          <div class="top-actions">
            <label class="theme-picker" title="Theme" data-i18n-title="theme.label">
              <span data-i18n="theme.label">Theme</span>
              <select id="theme-select" aria-label="Theme" data-i18n-aria-label="theme.label">
                <option value="dark-gata">Gata Dark</option>
                <option value="dark-dugout">Dugout Dark</option>
                <option value="dark-warpstone">Warpstone Dark</option>
                <option value="light-parchment">Parchment Light</option>
                <option value="light-sideline">Sideline Light</option>
                <option value="light-altdorf">Altdorf Light</option>
              </select>
            </label>
            <button id="auth-button" class="icon-text-button auth-button" type="button" data-i18n="auth.login">Login</button>
            <button id="lang-toggle" class="icon-text-button" type="button" title="Switch to Russian">EN</button>
          </div>
        </header>
```
(Theme names themselves — "Gata Dark", "Dugout Dark", etc. — stay in English in both locales: they're brand-flavored proper names for the color schemes, not descriptive UI copy, and `#theme-select`'s `<option>` values are used verbatim as CSS theme identifiers via `data-theme`. Leave the `<button id="auth-button">`'s `textContent` alone at runtime — it's overwritten dynamically by `updateAuthButton()`, handled in Step 4 below; the `data-i18n="auth.login"` here only covers the pre-JS instant and the signed-out state.)

- [ ] **Step 3: Add `data-i18n*` to the auth modal's static markup**

Replace the entire `<div id="auth-modal" ...>...</div>` block with:
```html
    <div id="auth-modal" class="auth-modal" hidden role="dialog" aria-modal="true" aria-labelledby="auth-title">
      <button class="auth-backdrop" type="button" data-auth-close aria-label="Close authorization" data-i18n-aria-label="auth.closeAriaLabel"></button>
      <section class="auth-dialog">
        <header>
          <h2 id="auth-title" data-i18n="auth.login">Login</h2>
          <button class="ghost-button" type="button" data-auth-close data-i18n="auth.close">Close</button>
        </header>

        <div id="auth-account" class="auth-account" hidden>
          <p id="auth-account-text"></p>
          <form id="auth-profile-form" class="auth-form">
            <label class="filter-field">
              <span data-i18n="auth.loginField">Login</span>
              <input name="login" autocomplete="username" required>
            </label>
            <label class="filter-field">
              <span data-i18n="auth.telegramField">Telegram contact</span>
              <input name="telegram" autocomplete="off" required>
            </label>
            <label class="filter-field">
              <span data-i18n="auth.newPasswordField">New password</span>
              <input name="password" type="password" autocomplete="new-password" placeholder="Leave empty to keep current" data-i18n-placeholder="auth.newPasswordPlaceholder">
            </label>
            <button class="primary-button" type="submit" data-i18n="auth.saveProfile">Save profile</button>
          </form>
          <button id="auth-logout" class="primary-button" type="button" data-i18n="auth.logout">Log out</button>
        </div>

        <form id="auth-form" class="auth-form">
          <label class="filter-field">
            <span data-i18n="auth.loginField">Login</span>
            <input name="login" autocomplete="username" required>
          </label>
          <label class="filter-field">
            <span data-i18n="auth.passwordField">Password</span>
            <input name="password" type="password" autocomplete="current-password" required>
          </label>
          <label class="filter-field" data-auth-telegram>
            <span data-i18n="auth.telegramField">Telegram contact</span>
            <input name="telegram" autocomplete="off" placeholder="@username">
          </label>
          <p id="auth-error" class="auth-error" hidden></p>
          <button id="auth-submit" class="primary-button" type="submit" data-i18n="auth.login">Login</button>
          <button id="auth-switch" class="filter-button" type="button" data-i18n="auth.createAccount">Create account</button>
        </form>
      </section>
    </div>
```

- [ ] **Step 4: Translate the dynamic auth-modal text in `src/app.js`**

Find `updateAuthButton` (currently `src/app.js:291-300`):
```js
function updateAuthButton() {
  if (!authButton) return;
  if (state.auth.currentUser) {
    authButton.textContent = state.auth.currentUser.login;
    authButton.title = `Signed in as ${state.auth.currentUser.login}`;
  } else {
    authButton.textContent = "Login";
    authButton.title = "Login or create account";
  }
}
```
Replace with:
```js
function updateAuthButton() {
  if (!authButton) return;
  if (state.auth.currentUser) {
    authButton.textContent = state.auth.currentUser.login;
    authButton.title = `${t("auth.signedInAs")} ${state.auth.currentUser.login}`;
  } else {
    authButton.textContent = t("auth.login");
    authButton.title = t("auth.loginOrCreate");
  }
}
```

Find `setAuthMode` (currently `src/app.js:302-341`):
```js
  if (authTitle) {
    authTitle.textContent = isAccount ? "Account" : isRegister ? "Register" : "Login";
  }
```
Replace with:
```js
  if (authTitle) {
    authTitle.textContent = isAccount ? t("auth.account") : isRegister ? t("auth.register") : t("auth.login");
  }
```

Further down in the same function:
```js
  if (authSubmit) {
    authSubmit.textContent = isRegister ? "Register" : "Login";
  }
  if (authSwitch) {
    authSwitch.textContent = isRegister ? "I already have an account" : "Create account";
  }
```
Replace with:
```js
  if (authSubmit) {
    authSubmit.textContent = isRegister ? t("auth.register") : t("auth.login");
  }
  if (authSwitch) {
    authSwitch.textContent = isRegister ? t("auth.haveAccount") : t("auth.createAccount");
  }
```

- [ ] **Step 5: Make `setAuthMode`/`updateAuthButton` re-run when the locale changes**

Find `applyLocaleChrome` (added in Task 2, Step 4) and add a call so open/closed auth UI re-translates immediately on switch. Replace:
```js
function applyLocaleChrome() {
  document.documentElement.lang = state.locale;
  activeDict = translations[state.locale];
  applyStaticI18n();
  if (langToggle) {
```
With:
```js
function applyLocaleChrome() {
  document.documentElement.lang = state.locale;
  activeDict = translations[state.locale];
  applyStaticI18n();
  updateAuthButton();
  setAuthMode(state.auth.mode);
  if (langToggle) {
```

- [ ] **Step 6: Add every key introduced in this task to both dictionaries**

Merge into `src/i18n/en.json` (add these keys alongside the ones from Task 2 — keep the file as one flat JSON object):
```json
{
  "nav.overview": "Overview",
  "nav.references": "References",
  "nav.inducements": "Inducements",
  "nav.skills": "Skills",
  "nav.traits": "Traits",
  "nav.starPlayers": "Star Players",
  "nav.teamsRules": "Team's Rules",
  "nav.builder": "Team Builder",
  "nav.myTeams": "My Teams",
  "nav.openMenu": "Open menu",
  "footer.loadingData": "Loading data",
  "footer.unofficialNote": "Unofficial fan-made league reference.",
  "footer.legalLink": "Legal Information",
  "search.placeholder": "Search teams, skills, rules...",
  "theme.label": "Theme",
  "auth.login": "Login",
  "auth.close": "Close",
  "auth.closeAriaLabel": "Close authorization",
  "auth.loginField": "Login",
  "auth.telegramField": "Telegram contact",
  "auth.newPasswordField": "New password",
  "auth.newPasswordPlaceholder": "Leave empty to keep current",
  "auth.saveProfile": "Save profile",
  "auth.logout": "Log out",
  "auth.passwordField": "Password",
  "auth.createAccount": "Create account",
  "auth.haveAccount": "I already have an account",
  "auth.signedInAs": "Signed in as",
  "auth.loginOrCreate": "Login or create account",
  "auth.account": "Account",
  "auth.register": "Register"
}
```

Merge into `src/i18n/ru.json`:
```json
{
  "nav.overview": "Обзор",
  "nav.references": "Справочник",
  "nav.inducements": "Инducements",
  "nav.skills": "Skills",
  "nav.traits": "Traits",
  "nav.starPlayers": "Star Players",
  "nav.teamsRules": "Правила команд",
  "nav.builder": "Конструктор команды",
  "nav.myTeams": "Мои команды",
  "nav.openMenu": "Открыть меню",
  "footer.loadingData": "Загрузка данных",
  "footer.unofficialNote": "Неофициальный фанатский справочник по лиге.",
  "footer.legalLink": "Юридическая информация",
  "search.placeholder": "Поиск команд, навыков, правил...",
  "theme.label": "Тема",
  "auth.login": "Вход",
  "auth.close": "Закрыть",
  "auth.closeAriaLabel": "Закрыть окно авторизации",
  "auth.loginField": "Логин",
  "auth.telegramField": "Контакт в Telegram",
  "auth.newPasswordField": "Новый пароль",
  "auth.newPasswordPlaceholder": "Оставьте пустым, чтобы не менять",
  "auth.saveProfile": "Сохранить профиль",
  "auth.logout": "Выйти",
  "auth.passwordField": "Пароль",
  "auth.createAccount": "Создать аккаунт",
  "auth.haveAccount": "У меня уже есть аккаунт",
  "auth.signedInAs": "Вы вошли как",
  "auth.loginOrCreate": "Войти или создать аккаунт",
  "auth.account": "Аккаунт",
  "auth.register": "Регистрация"
}
```

Note on `nav.inducements`/`nav.skills`/`nav.traits`: these route names double as Blood Bowl category keywords the glossary says to keep in English (Skills/Traits/Inducements are the actual game-mechanic category names, same as "Skill" or "Trait" appearing on a card) — deliberately identical in both dictionaries.

- [ ] **Step 7: Manually verify**

Run `npm run dev`, reload, toggle locale. Confirm: every nav link, the search placeholder, the theme label, and the auth modal (open it via the Login button) all switch between English and Russian text with no leftover hardcoded English when in `ru`, and no broken layout.

- [ ] **Step 8: Commit**

```bash
git add index.html src/app.js src/i18n/en.json src/i18n/ru.json
git commit -m "Translate static shell: sidebar, topbar, and auth modal"
```

---

### Task 4: Translate reference-browsing views

**Files:**
- Modify: `src/app.js` — functions `renderHeader` (1041), `renderHome` (1053), `renderSimpleCard` (1100), `renderSection` (1136), `renderFilters` (1155), `renderTeamFilters` (1167), `renderSkillFilters` (1219), `renderStarFilters` (1233), `renderInducementFilters` (1247), `renderListCard` (1286), `renderDetail` (1322), `renderRosterLinks` (1366), `renderRosterValues` (1376), `renderRuleLinks` (1488), `renderTeamRuleAccess` (1556), `renderPagePills` (1613), `renderLeaguesReferencePage` (1618), `renderRosterStatGrid` (1649), `renderTeamRosterMobile` (1661), `renderSkillTableRoller` (1701), `renderReferenceTableMobile` (1763), `renderSkillTableMobile` (1796), `renderSidebar` (1843), `renderLegal` (1889)
- Modify: `src/i18n/en.json`, `src/i18n/ru.json`

**Interfaces:**
- Consumes: `t(key)` from Task 2.
- Produces: nothing new — leaf task.

**Ground rule for every step below:** only replace strings that are pure UI chrome (labels, button text, empty-state copy, filter option labels). Never touch a value read from `page`/`team`/`skill`/`state.data.*` — those come pre-translated from `data.<locale>.json` once Tasks 8-14 translate the content vault. If a string is ambiguous, check whether it interpolates a `${page.xxx}`/`${team.xxx}` variable — if it does, only the surrounding literal text is a translation target, not the interpolated value.

- [ ] **Step 1: Worked example — convert `renderLegal` completely**

Find (`src/app.js:1889-1900`):
```js
function renderLegal() {
  setActiveNav("legal");
  setViewSection("pages");
  view.innerHTML = `
    ${renderHeader("Legal Information", "Unofficial fan-made league reference for a private Blood Bowl league.")}
    <article class="content-panel content-body">
      <p>Gata Blood Bowl League is an unofficial fan reference. It is not affiliated with, endorsed by, or sponsored by Games Workshop.</p>
      <p>Blood Bowl and related names belong to their respective owners. This site is intended to document league-specific house rules and help players navigate their local league.</p>
      <p>Base game wording is referenced through Blood Bowl Base where appropriate instead of being reproduced here in full.</p>
    </article>
  `;
}
```
Replace with:
```js
function renderLegal() {
  setActiveNav("legal");
  setViewSection("pages");
  view.innerHTML = `
    ${renderHeader(t("legal.title"), t("legal.subtitle"))}
    <article class="content-panel content-body">
      <p>${t("legal.paragraph1")}</p>
      <p>${t("legal.paragraph2")}</p>
      <p>${t("legal.paragraph3")}</p>
    </article>
  `;
}
```
Add to `src/i18n/en.json`:
```json
{
  "legal.title": "Legal Information",
  "legal.subtitle": "Unofficial fan-made league reference for a private Blood Bowl league.",
  "legal.paragraph1": "Gata Blood Bowl League is an unofficial fan reference. It is not affiliated with, endorsed by, or sponsored by Games Workshop.",
  "legal.paragraph2": "Blood Bowl and related names belong to their respective owners. This site is intended to document league-specific house rules and help players navigate their local league.",
  "legal.paragraph3": "Base game wording is referenced through Blood Bowl Base where appropriate instead of being reproduced here in full."
}
```
Add to `src/i18n/ru.json`:
```json
{
  "legal.title": "Юридическая информация",
  "legal.subtitle": "Неофициальный фанатский справочник для частной лиги Blood Bowl.",
  "legal.paragraph1": "Gata Blood Bowl League — неофициальный фанатский справочник. Проект не аффилирован с Games Workshop, не одобрен и не спонсируется компанией.",
  "legal.paragraph2": "Blood Bowl и связанные названия принадлежат их правообладателям. Этот сайт документирует внутренние правила лиги и помогает игрокам ориентироваться в своей лиге.",
  "legal.paragraph3": "Формулировки базовых правил приводятся со ссылкой на Blood Bowl Base там, где это уместно, вместо полного воспроизведения текста здесь."
}
```
("Gata Blood Bowl League" and "Blood Bowl Base" stay in English in both — they're the proper names of the league and the reference source.)

- [ ] **Step 2: Apply the same pattern to every other function in this task's scope**

For each function listed in this task's **Files** section (aside from `renderLegal`, done in Step 1): find every literal English string in its template — headings, button labels, "no results" / empty-state text, filter `<option>` labels such as "All types"/"All leagues" in `renderTeamFilters`, table column headers like "Qty"/"Position"/"Skills" in `renderRosterStatGrid`/`renderTeamRosterMobile` (these table headers describe roster columns and are UI labels, not the position/skill names themselves, so they get translated), roll-table UI text in `renderSkillTableRoller`. For each one:
1. Add a `t()`-backed key to both `src/i18n/en.json` (English value = the current literal string, unchanged) and `src/i18n/ru.json` (Russian translation).
2. Replace the literal string in the template with `${t("your.key")}`.
3. If the same literal string is reused verbatim by more than one function in this list (e.g. "All" appearing in multiple filter dropdowns), reuse the same key rather than creating a duplicate.

- [ ] **Step 3: Grep for stray literal English after the sweep**

Run: `grep -n '>[A-Z][a-z]' src/app.js | sed -n '1041,1920p'` won't work directly by line range with grep; instead run a targeted check per function, e.g.:
```bash
sed -n '1041,1920p' src/app.js | grep -nE '"[A-Z][a-zA-Z '\''.,!?-]{2,}"' 
```
Expected: every match remaining is either (a) a `t("...")` key string (fine), (b) a CSS class name or HTML attribute value (fine), or (c) a value clearly sourced from `page`/`team`/content data (fine, translated via the vault). If you find a literal UI string that isn't any of those, it was missed — go back and extract it.

- [ ] **Step 4: Manually verify**

Run `npm run dev`. In both locales, visit: Overview (`#/`), References (`#/pages`), Inducements (`#/inducements`), Skills (`#/skills`), Traits (`#/traits`), Star Players (`#/star-players`), Team's Rules (`#/teams`), and open one detail page from each list, plus `#/legal`. Confirm all chrome (headings, filter labels, empty states, table column headers) is in the active locale, and that team/skill/page names/descriptions are unaffected (still English — Tasks 8-14 haven't translated content yet).

- [ ] **Step 5: Commit**

```bash
git add src/app.js src/i18n/en.json src/i18n/ru.json
git commit -m "Translate reference-browsing view chrome"
```

---

### Task 5: Translate My Teams / Saved Roster views

**Files:**
- Modify: `src/app.js` — functions `renderMyTeams` (1921), `renderSavedTeamsTable` (1950), `renderSavedTeamRow` (1974), `renderSavedRoster` (2018), `renderSavedRosterSummary` (2077), `renderSavedRosterSettings` (2115), `renderRosterAddon` (2168), `renderRosterStaffControl` (2181), `renderRosterSlot` (2241), `renderSlotPlayerEditor` (2278), `renderRosterStepper` (2331)
- Modify: `src/i18n/en.json`, `src/i18n/ru.json`

**Interfaces:**
- Consumes: `t(key)` from Task 2.
- Produces: nothing new — leaf task.

Same ground rule as Task 4: only literal UI chrome, never content-derived values (team names, skill names, player names the user entered are user data — never translated).

- [ ] **Step 1: Worked example — convert `renderMyTeams`**

Find (`src/app.js:1921-1928`):
```js
async function renderMyTeams() {
  setActiveNav("my-teams");
  setViewSection("teams");
  view.innerHTML = `
    ${renderHeader("My Teams", "Saved teams from your profile.", `<button class="primary-button" type="button" data-new-team>Create Team</button>`)}
    <div class="loading">Loading teams...</div>
  `;
  await loadMyTeams(true);
```
Replace with:
```js
async function renderMyTeams() {
  setActiveNav("my-teams");
  setViewSection("teams");
  view.innerHTML = `
    ${renderHeader(t("myTeams.title"), t("myTeams.subtitle"), `<button class="primary-button" type="button" data-new-team>${t("myTeams.createTeam")}</button>`)}
    <div class="loading">${t("myTeams.loadingTeams")}</div>
  `;
  await loadMyTeams(true);
```
Add to `src/i18n/en.json`:
```json
{
  "myTeams.title": "My Teams",
  "myTeams.subtitle": "Saved teams from your profile.",
  "myTeams.createTeam": "Create Team",
  "myTeams.loadingTeams": "Loading teams..."
}
```
Add to `src/i18n/ru.json`:
```json
{
  "myTeams.title": "Мои команды",
  "myTeams.subtitle": "Сохранённые команды вашего профиля.",
  "myTeams.createTeam": "Создать команду",
  "myTeams.loadingTeams": "Загрузка команд..."
}
```

- [ ] **Step 2: Apply the same pattern to the rest of this task's functions**

Same process as Task 4 Step 2: table headers ("Roster", "Value", "Actions" style columns in `renderSavedTeamsTable`/`renderSavedTeamRow`), button labels ("Save Changes", "Copy Roster", "Delete", "Edit"), roster-editor labels/tooltips in `renderRosterAddon`/`renderRosterStaffControl`/`renderRosterSlot`/`renderSlotPlayerEditor`/`renderRosterStepper`, and the summary/settings copy in `renderSavedRosterSummary`/`renderSavedRosterSettings`. Add a key pair per string, replace the literal with `t()`.

Watch for interpolated status strings such as (around `src/app.js:2369` and `2458-2467`):
```js
if (treasuryDisplay) treasuryDisplay.textContent = `${countToNumber(draft.treasury)}k`;
...
if (rowTotal) rowTotal.textContent = `${playerSppTotal(team, player)} SPP earned`;
if (available) available.textContent = `${playerAvailableSpp(team, player)} SPP available`;
if (nextAdvancement) nextAdvancement.textContent = `Next: ${nextRank.rank}, ${playerAvailableSpp(team, player)} SPP available`;
if (rosterTotal) rosterTotal.textContent = `${rosterTotalSpp(team, draft)} SPP`;
```
`SPP` is glossary-protected core stat shorthand (stays as-is in both locales) — only translate the surrounding words ("earned", "available", "Next:"). For example:
```js
if (rowTotal) rowTotal.textContent = `${playerSppTotal(team, player)} ${t("roster.sppEarned")}`;
if (available) available.textContent = `${playerAvailableSpp(team, player)} ${t("roster.sppAvailable")}`;
if (nextAdvancement) nextAdvancement.textContent = `${t("roster.next")}: ${nextRank.rank}, ${playerAvailableSpp(team, player)} ${t("roster.sppAvailable")}`;
```
where `nextRank.rank` (e.g. "Veteran", "Star") is a Blood Bowl advancement-rank keyword and stays untranslated per glossary. Add `roster.sppEarned` ("SPP earned" / "SPP получено"), `roster.sppAvailable` ("SPP available" / "SPP доступно"), `roster.next` ("Next" / "Далее") to both dictionaries.

- [ ] **Step 3: Manually verify**

Log in (or create a test account), save a team via the builder, then visit `#/my-teams` and open the saved roster in both locales. Confirm every button/label/status string switches language, SPP/stat numbers and team/player/skill names are untouched.

- [ ] **Step 4: Commit**

```bash
git add src/app.js src/i18n/en.json src/i18n/ru.json
git commit -m "Translate My Teams and saved roster view chrome"
```

---

### Task 6: Translate Team Builder views

**Files:**
- Modify: `src/app.js` — functions `renderBuilder` (2674), `renderBuilderSummary` (2749), `renderAvailablePlayerTable` (2775), `renderBuilderStaffControl` (2826), `renderPlainSkillPills` (2844), `renderAccessCell` (2849), `renderRosterStatCells` (2854), `renderPlayerStatCells` (2860), `renderEditablePlayerStatCells` (2869), `renderBuilderPlayerList` (2888), `renderBuilderPlayerRow` (2919), `renderEditableStatLine` (3211), `renderAddon` (3233), `renderBuilderRow` (3246), `renderBuilderSummaryRoster` (3359), `renderEditableRosterPlayers` (3363), `renderEditablePlayer` (3387), `renderStepper` (3434)
- Modify: the Team Builder's own "Copy Roster"/"Saved" button handler (its `copyRoster`/`saveTeam` wiring — do not touch the Saved Roster page's separate, already-translated `copySavedRoster`/`saveSavedRoster` pair)
- Modify: `src/i18n/en.json`, `src/i18n/ru.json`

**Interfaces:**
- Consumes: `t(key)` from Task 2.
- Produces: nothing new — leaf task.

**Correction (found during Task 5):** this plan originally also listed `renderSavedPlayerList`, `renderSavedNewPlayerTable`, `renderSavedPlayerRow`, `renderSavedPlayerCard`, `renderPlayerSppControls`, `renderPlayerLevelCell`, `renderPlayerAdvancementControls` here. Those functions render the Saved Roster page's player table (not the Team Builder's), so Task 5 already translated them — they've been removed from this task's file list above. Task 6 should **not** re-touch them; reuse their existing keys (`roster.sppEarned`, `roster.sppAvailable`, `roster.next`, `roster.nameHeader`, `roster.positionHeader`, `roster.skillsLabel`, `roster.levelHeader`, `roster.advancementHeader`, etc. — check `src/i18n/en.json` for the full set Task 5 added) wherever the Team Builder's own analogous functions (`renderBuilderPlayerList`/`renderBuilderPlayerRow`/`renderAvailablePlayerTable`/etc.) use the identical literal string. Task 5 also already left the Team Builder's own `copyRoster`/`saveTeam` "Copied"/"Saved" transient-label pair untouched specifically for this task to handle, and recommends reusing `roster.copyRoster`/`roster.copiedStatus`/`roster.savedStatus`/`roster.saveChanges` for it rather than inventing new keys — those keys already exist from Task 5, confirm the literal strings match before reusing.

Same ground rule as Tasks 4 and 5. Column headers like "Skills" that appear in the Team Builder's own tables are UI labels, translate them (reusing Task 5's `roster.skillsLabel` etc. where the literal matches); the actual skill names inside those columns come from content data, don't touch them.

- [ ] **Step 1: Worked example — convert the Team Builder's own transient button-label swap**

**Correction (found during Task 5):** the plan originally pointed this step at `src/app.js:2652-2670`. That location turned out to be the Saved Roster page's own save/copy handlers (`saveSavedRoster`/`copySavedRoster`), which Task 5 already translated using keys `roster.saveChanges`, `roster.savedStatus`, `roster.copyRoster`, `roster.copiedStatus` — do not re-touch that code or re-invent keys for it. This step is about the **Team Builder's own**, separate `copyRoster`/`saveTeam` functions (Task 5's report locates them around `src/app.js:3799-3841`, though the exact line will have shifted further by the time you start — find them by function name, not line number).

Find, in `saveTeam` (or equivalent — search for the literal strings if the function has been renamed):
```js
        button.textContent = "Saved";
        setTimeout(() => { button.textContent = "Save Changes"; }, 1200);
```
and, in `copyRoster`:
```js
    button.textContent = "Copied";
    setTimeout(() => { button.textContent = "Copy Roster"; }, 1200);
```
Replace with:
```js
        button.textContent = t("roster.savedStatus");
        setTimeout(() => { button.textContent = t("roster.saveChanges"); }, 1200);
```
and:
```js
    button.textContent = t("roster.copiedStatus");
    setTimeout(() => { button.textContent = t("roster.copyRoster"); }, 1200);
```
**Reuse Task 5's existing keys** (`roster.savedStatus`, `roster.saveChanges`, `roster.copiedStatus`, `roster.copyRoster`) — do not add new `builder.*` keys for this; confirm first that the literal English strings in the Team Builder's version match Task 5's Saved Roster version exactly (both should read "Saved"/"Save Changes"/"Copied"/"Copy Roster") before reusing. If any literal differs even slightly, flag it and ask rather than silently reusing a mismatched key.

- [ ] **Step 2: Apply the same pattern to every function in this task's scope**

Work through the function list top to bottom. For each: labels ("Skills" column headers, "Value", "Cost", stat-block headers), buttons ("Add", "Remove", "Reset", stepper +/- `aria-label`s in `renderStepper`/`renderRosterStepper`), staff/addon descriptions in `renderBuilderStaffControl`/`renderAddon` (these describe purchasable staff like Cheerleaders/Assistant Coaches — the staff *names* are Blood Bowl keywords and stay in English per glossary; only the surrounding sentence describing cost/limit is translated), and advancement-related labels in `renderPlayerAdvancementControls`/`renderPlayerLevelCell` (recall `advancementRanks`/`advancementTypeLabels` at `src/app.js:147-159` hold rank/type *names* like "Veteran"/"Primary" — those are keywords, stay in English; only surrounding UI text like "Next advancement" gets a key).

- [ ] **Step 3: Grep for stray literal English**

Run the same style of check as Task 4 Step 3, scoped to this task's line range (`sed -n '2674,3770p' src/app.js | grep -nE '"[A-Z][a-zA-Z '\''.,!?-]{2,}"'`). Confirm every remaining hit is a `t()` key, a class/attribute value, or genuinely content-sourced.

- [ ] **Step 4: Manually verify**

Run `npm run dev`, open `#/builder` in both locales, add players from a couple of different teams, exercise every control (add/remove player, stat editing, staff purchases, save/copy roster), confirm every button, label, and tooltip switches with the locale while team/player/skill names stay in English.

- [ ] **Step 5: Commit**

```bash
git add src/app.js src/i18n/en.json src/i18n/ru.json
git commit -m "Translate Team Builder view chrome"
```

---

### Task 7: i18n glossary doc + structural verification script

**Files:**
- Create: `docs/i18n-glossary.md`
- Create: `scripts/check-i18n-glossary.mjs`
- Modify: `package.json` (add an `i18n:check` script)

**Interfaces:**
- Produces: `docs/i18n-glossary.md` — read by every content-translation task from here on (Tasks 8-14).
- Produces: `npm run i18n:check` — diffs identifier fields between `public/data.en.json` and `public/data.ru.json`, used as the mechanical check in every content-translation task and in the final QA (Task 15).

- [ ] **Step 1: Write the glossary doc**

Create `docs/i18n-glossary.md`:
```markdown
# i18n Glossary — Terms That Stay in English

When translating `content/Gata` into `content/Gata-ru`, or writing Russian UI
strings, the following categories are **never translated**, in either locale:

- **Team/race names** — Human, Orc, Chaos Dwarfs, Amazon, Old World Alliance, etc.
- **Skill and trait names** — Block, Dodge, Mighty Blow, Regeneration, etc. (the
  name only — the description text around it is translated).
- **Player positions** — Lineman, Blitzer, Thrower, Big Guy, etc.
- **Star player names** — Griff Oberwald, Asperon Thorn, etc.
- **Inducement and special-rule names** — Bribe, Biased Referee, Wandering
  Apothecary, Lustrian Superleague, etc. (the name only — surrounding
  descriptive prose is translated).
- **Core stat shorthand** — MA, ST, AG, PA, AV/AR, SPP, TV, GP, CAS.
- **Advancement rank and type names** — Rookie, Experienced, Veteran, Emerging
  Star, Star, Superstar, Legend, and Random/Primary/Secondary/Stat.

## Structural bold-label markers

`scripts/build-data.mjs` parses a few fixed bold-label lines out of team and
star player pages to populate structured fields (roster meta, builder costs).
When translating those specific lines, use these exact Russian phrasings —
anything else won't be recognized by the parser:

| English            | Russian (use exactly this) | Used on         |
|---------------------|------------------------------|-----------------|
| **Rerolls:**         | **Перебросы:**                | Team pages      |
| **Apothecary:**       | **Апотекарий:**               | Team pages      |
| **League:**           | **Лига:**                     | Team pages      |
| **Special Rules:**    | **Специальные правила:**      | Team pages      |
| **Availability:**     | **Доступность:**              | Star player pages |
| **Cost:**             | **Цена:**                     | Star player pages |
| **Teams:**            | **Команды:**                  | Star player pages |

`**Name:**` and `**Special Ability:**` on star player pages are *not* parsed
into structured fields (pure display prose) — translate them freely, e.g.
`**Имя:**` / `**Персональная способность:**`.

## Inducement names used as UI labels elsewhere

**Ruling from Task 6:** some inducement names double as roster-builder staff
purchase labels (e.g. "Assistant Coaches" and "Cheerleaders" are both named
inducements with their own page under `Inducements/`, *and* labels on the
Team Builder / Saved Roster staff-purchase controls). Wherever a UI label is
the same string as a named inducement, it stays in English in both locales,
everywhere it appears — not just on the inducement's own content page. Don't
translate it as generic UI copy just because it also functions as a button
label. A UI label that does *not* match a named inducement (e.g. "Dedicated
Fans," which has no corresponding `Inducements/` page) is ordinary UI copy
and gets translated normally.

## Filenames and folder names

`content/Gata-ru/` must mirror `content/Gata/`'s file and folder names
byte-for-byte. Never rename a file or folder when translating — identifiers
(skill name, star player name, team name) are derived from the filename by
`scripts/build-data.mjs`, so renaming breaks the site.

## What *is* translated

Everything else: rule explanations, casualty/weather/kick-off table effect
text, inducement descriptions, skill/trait "Rule summary" and "Gata League
change" prose, star player special-ability descriptions, and any other
narrative text. Markdown table structure, `[[wiki-links]]` targets, and
frontmatter `tags:` values are never translated (tags are filter/category
keywords, e.g. `Agility`, `Trait`, `Inducement`).
```

- [ ] **Step 2: Write the structural verification script**

Create `scripts/check-i18n-glossary.mjs`:
```js
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const publicDir = path.join(rootDir, "public");

function loadJson(filePath) {
  return fs.readFile(filePath, "utf8").then((raw) => JSON.parse(raw));
}

function collectIdentifiers(data) {
  const byId = new Map();
  for (const page of data.pages) {
    byId.set(page.id, { title: page.title, section: page.section, path: page.path });
  }
  return byId;
}

const [enData, ruData] = await Promise.all([
  loadJson(path.join(publicDir, "data.en.json")),
  loadJson(path.join(publicDir, "data.ru.json")),
]);

const enPages = collectIdentifiers(enData);
const ruPages = collectIdentifiers(ruData);

const mismatches = [];

for (const [id, enPage] of enPages) {
  const ruPage = ruPages.get(id);
  if (!ruPage) {
    mismatches.push(`Missing in RU data: ${enPage.path} (id: ${id})`);
    continue;
  }
  if (ruPage.title !== enPage.title) {
    mismatches.push(`Title mismatch for ${enPage.path}: EN "${enPage.title}" vs RU "${ruPage.title}"`);
  }
  if (ruPage.path !== enPage.path) {
    mismatches.push(`Path mismatch for id ${id}: EN "${enPage.path}" vs RU "${ruPage.path}"`);
  }
}

for (const id of ruPages.keys()) {
  if (!enPages.has(id)) {
    mismatches.push(`Extra page in RU data with no EN counterpart: ${ruPages.get(id).path} (id: ${id})`);
  }
}

if (mismatches.length > 0) {
  console.error(`i18n glossary check failed with ${mismatches.length} issue(s):`);
  for (const issue of mismatches) {
    console.error(`  - ${issue}`);
  }
  process.exit(1);
}

console.log(`i18n glossary check passed: ${enPages.size} pages have matching identifiers in both locales.`);
```

- [ ] **Step 3: Add the npm script**

In `package.json`, find:
```json
    "build": "node scripts/build-data.mjs && node scripts/build-site.mjs",
```
Add directly below it:
```json
    "build": "node scripts/build-data.mjs && node scripts/build-site.mjs",
    "i18n:check": "node scripts/check-i18n-glossary.mjs",
```

- [ ] **Step 4: Run it against the current (untranslated) build to confirm it passes trivially**

Run: `npm run build && npm run i18n:check`
Expected output ends with:
```
i18n glossary check passed: 299 pages have matching identifiers in both locales.
```
(This is a trivial pass right now since `data.ru.json` is still a copy of `data.en.json` — Task 8 onward will start making them genuinely differ while keeping this check green.)

- [ ] **Step 5: Commit**

```bash
git add docs/i18n-glossary.md scripts/check-i18n-glossary.mjs package.json
git commit -m "Add i18n glossary doc and structural verification script"
```

---

### Task 8: Translate content — Rules

**Files:**
- Create: `content/Gata-ru/Rules/1. League Basics.md`
- Create: `content/Gata-ru/Rules/2. Team Creation.md`
- Create: `content/Gata-ru/Rules/3. Team Management.md`
- Create: `content/Gata-ru/Rules/4. Match Procedures.md`
- Create: `content/Gata-ru/Rules/5. Patch Notes.md`

**Interfaces:**
- Consumes: `docs/i18n-glossary.md` (Task 7), `npm run i18n:check` (Task 7).
- Produces: translated pages consumed by `scripts/build-data.mjs`'s `buildLocaleData(ruVaultDir)` (Task 1) once `content/Gata-ru` exists — this is the first task where the RU vault directory actually appears, so it's also the first task where `npm run i18n:check` will process **real** translated content instead of a copy.

- [ ] **Step 1: Worked example — translate `1. League Basics.md`**

Read the source: `content/Gata/Rules/1. League Basics.md`. Its content (verified against the current repo) is:
```markdown
# 1. League Basics

Blood Bowl 2025 + homebrew

Gata League 2:  Info

Minis

Good vibes

A set of Dice

How to Be a Great Player

Play fair and with respect for your opponent.

Rollbacks are allowed for any actions, but only before the dice are thrown.

Control your frustration ("tilt") over the dice rolls.

Report match results to the organizer on time.

Ask the organizer immediately if you have any questions about the rules that you cannot find the answer to.

Notify in advance if you cannot play your match on time.

Enjoy the football!
```
Create `content/Gata-ru/Rules/1. League Basics.md`:
```markdown
# 1. Основы лиги

Blood Bowl 2025 + доморощенные правила

Gata League 2: Информация

Миниатюры

Хорошее настроение

Набор кубиков

Как быть отличным игроком

Играйте честно и с уважением к сопернику.

Откат действий разрешён для любых действий, но только до броска кубиков.

Контролируйте своё раздражение ("тильт") из-за результатов бросков.

Своевременно сообщайте организатору результаты матчей.

Сразу спрашивайте организатора, если у вас есть вопросы по правилам, на которые вы не можете найти ответ.

Заранее предупреждайте, если не можете сыграть свой матч вовремя.

Наслаждайтесь футболом!
```
("Blood Bowl 2025" and "Gata League" stay in English — proper names/product title.)

- [ ] **Step 2: Translate the remaining 4 files in this folder**

For each of `2. Team Creation.md`, `3. Team Management.md`, `4. Match Procedures.md`, `5. Patch Notes.md`: read the source file under `content/Gata/Rules/`, translate every sentence into Russian following the same pattern as Step 1 (headings translated except proper nouns, glossary terms — team names, skill/position names, "Gata League"/"Blood Bowl" — kept in English), and write the result to the identically-named file under `content/Gata-ru/Rules/`. Preserve Markdown structure (headings, lists, tables, links) exactly — only the human-readable text changes language.

- [ ] **Step 3: Rebuild and run the verification script**

Run: `npm run build && npm run i18n:check`
Expected: build succeeds, `i18n:check` still passes (page count and identifiers unchanged — only prose differs), and:
```bash
diff public/data.en.json public/data.ru.json | head -5
```
now shows real differences (previously identical, Task 1 Step 8 confirmed `IDENTICAL` — this is the first task where that stops being true).

- [ ] **Step 4: Spot-check against the glossary**

Open 2 of the 5 translated files side-by-side with their English source. Confirm: every team/skill/position name that appears mid-sentence is still in English, "Blood Bowl"/"Gata League" are untranslated, and the rest reads as natural Russian.

- [ ] **Step 5: Commit**

```bash
git add content/Gata-ru/Rules
git commit -m "Translate Rules content to Russian"
```

---

### Task 9: Translate content — General Information

**Files:**
- Create: `content/Gata-ru/General Information/All Gata Changes.md`
- Create: `content/Gata-ru/General Information/Casualties.md`
- Create: `content/Gata-ru/General Information/Kick-off Table.md`
- Create: `content/Gata-ru/General Information/Leagues.md`
- Create: `content/Gata-ru/General Information/Player Advancement.md`
- Create: `content/Gata-ru/General Information/Prayers to Nuffle.md`
- Create: `content/Gata-ru/General Information/Reference Sources.md`
- Create: `content/Gata-ru/General Information/Special Rules.md`
- Create: `content/Gata-ru/General Information/Weather.md`

**Interfaces:**
- Consumes: `docs/i18n-glossary.md`, `npm run i18n:check`.

- [ ] **Step 1: Worked example — translate the table-heavy `Weather.md`**

Source `content/Gata/General Information/Weather.md` (excerpt, confirmed against the repo):
```markdown
## Spring

| 2d6 | d6 | Result | Effect |
| --- | --- | --- | --- |
| 2 | 1 | Morning Dew | -1 to Rush tests. -1 to all ball pick-up tests. |
| 3 | 2 | Pollen | The referee has allergies. Players are not Sent-off during Fouls. |
| 4-10 | 3-4 | Normal Weather | No additional effect. |
| 11 | 5 | Foggy Morning | Players' MA cannot exceed 6. Only Quick and Short passes are allowed. |
| 12 | 6 | Strong Wind | Team re-rolls work on a 2+. |
```
Create `content/Gata-ru/General Information/Weather.md` with the same table shape, translated:
```markdown
## Весна

| 2d6 | d6 | Результат | Эффект |
| --- | --- | --- | --- |
| 2 | 1 | Утренняя роса | -1 к тестам Rush. -1 ко всем тестам подбора мяча. |
| 3 | 2 | Пыльца | У судьи аллергия. Игроков не удаляют (Sent-off) за фолы. |
| 4-10 | 3-4 | Обычная погода | Без дополнительного эффекта. |
| 11 | 5 | Туманное утро | MA игроков не может превышать 6. Разрешены только передачи Quick и Short. |
| 12 | 6 | Сильный ветер | Командные переброски проходят на 2+. |
```
Apply the same pattern (translate weather-condition names and effect prose, keep `MA`/rule-action keywords like `Rush`/`Sent-off`/`Quick`/`Short` in English since they're Blood Bowl mechanic terms) to the remaining seasons in the same file (Summer, and any others present in the source) before moving to the next file. Table column headers ("2d6", "d6" stay as dice notation; "Result"/"Effect" are UI-like labels, translate them as shown).

- [ ] **Step 2: Translate the remaining 8 files**

For each of `All Gata Changes.md`, `Casualties.md`, `Kick-off Table.md`, `Leagues.md`, `Player Advancement.md`, `Prayers to Nuffle.md`, `Reference Sources.md`, `Special Rules.md`: read the English source, translate prose (including table cell text — these files are largely tables of effects, similar in shape to `Weather.md`), keep glossary terms (team/skill/position/special-rule names, stat shorthand) in English, preserve Markdown/table structure, write to the identically-named file under `content/Gata-ru/General Information/`. Note `Special Rules.md` contains the prose descriptions for named special rules like "Lustrian Superleague" (referenced from team pages) — translate the description, keep the rule's proper name in English and call it out clearly (e.g. as a bolded term) so it's recognizable as the same rule linked from team pages.

- [ ] **Step 3: Rebuild and verify**

Run: `npm run build && npm run i18n:check`. Expected: passes, page counts unchanged.

- [ ] **Step 4: Spot-check 3 files against the glossary**, as in Task 8 Step 4.

- [ ] **Step 5: Commit**

```bash
git add "content/Gata-ru/General Information"
git commit -m "Translate General Information content to Russian"
```

---

### Task 10: Translate content — Inducements

**Files:**
- Create all 24 files under `content/Gata-ru/Inducements/`, matching `content/Gata/Inducements/`'s current file list: `Additional Training.md`, `Assistant Coaches.md`, `Ballistics Expert.md`, `Biased Referee.md`, `Bloodweiser Keg.md`, `Bottles of Grape Day.md`, `Bribe.md`, `Cheerleaders.md`, `Frolicking Nurgling.md`, `Halfling Master Chef.md`, `Halfling Surprise Pot.md`, `Hired Wizard.md`, `Mark of Chaos.md`, `Mortuary Assistant.md`, `Nuffle's Prayers.md`, `Plague Doctor.md`, `Rowdy Rookies.md`, `Rune Priest.md`, `Star Players.md`, `Team Mascot.md`, `Vishnevsky Ointment.md`, `WAAAGH! Drummer.md`, `Wandering Apothecary.md`, `Weather Mage.md`

**Interfaces:**
- Consumes: `docs/i18n-glossary.md`, `npm run i18n:check`.

- [ ] **Step 1: Worked example — translate `Bribe.md`**

Source `content/Gata/Inducements/Bribe.md` (confirmed against the repo):
```markdown
---
tags:
  - Inducement
---

0-3 Bribe (100k, or 50k for Bribery and Corruption): When your player is sent off, you may spend a bribe to cancel this effect. The turnover is also canceled.
```
Create `content/Gata-ru/Inducements/Bribe.md`:
```markdown
---
tags:
  - Inducement
---

0-3 Bribe (100k, или 50k при Bribery and Corruption): когда вашего игрока удаляют с поля, вы можете потратить Bribe, чтобы отменить этот эффект. Turnover также отменяется.
```
(`tags: Inducement` stays in English — it's a filter/category keyword, not prose. "Bribe" itself is the inducement's proper name — glossary term, kept in English even inline. "Bribery and Corruption" and "Turnover" are Blood Bowl rule-keyword names — kept in English.)

- [ ] **Step 2: Translate the remaining 23 files**

For each remaining file in the list above: read the English source, translate the descriptive prose, keep the inducement's own name (matching its filename) untranslated wherever it appears inline, keep `tags:` frontmatter values in English, keep any other Blood Bowl keyword referenced in the description (skill names, other inducement names, rule names) in English, write to the identically-named file under `content/Gata-ru/Inducements/`.

- [ ] **Step 3: Rebuild and verify**

Run: `npm run build && npm run i18n:check`. Expected: passes.

- [ ] **Step 4: Spot-check 4 files against the glossary.**

- [ ] **Step 5: Commit**

```bash
git add content/Gata-ru/Inducements
git commit -m "Translate Inducements content to Russian"
```

---

### Task 11: Translate content — Skills

**Files:**
- Create `content/Gata-ru/Skills and Traits/Skill Table.md`
- Create all 93 files under `content/Gata-ru/Skills and Traits/Skills/` (one per file currently in `content/Gata/Skills and Traits/Skills/` — get the authoritative list by running `ls "content/Gata/Skills and Traits/Skills"` before starting)

**Interfaces:**
- Consumes: `docs/i18n-glossary.md`, `npm run i18n:check`.

- [ ] **Step 1: Get the exact file list**

Run: `ls "content/Gata/Skills and Traits/Skills" | sort`
This is your checklist — every name it prints needs a same-named file under `content/Gata-ru/Skills and Traits/Skills/` by the end of this task.

- [ ] **Step 2: Worked example — translate `Block.md` and `Dodge.md`**

Source `content/Gata/Skills and Traits/Skills/Block.md` (confirmed against the repo):
```markdown
---
tags:
  - Active
  - General
---

## Rule summary
When a Both Down result is applied in a Block involving this player, they may choose not to be Knocked Down.

Full wording: https://bloodbowlbase.ru/bb2025/core_rules/skills_and_traits/

## Gata League change
- During this player's own activation, when a Both Down result is applied in a Block involving this player, this player is not Knocked Down by that result. Outside this player's own activation, Block does not apply.
```
Create `content/Gata-ru/Skills and Traits/Skills/Block.md`:
```markdown
---
tags:
  - Active
  - General
---

## Краткое описание
Если при Block с участием этого игрока выпал результат Both Down, он может не считаться Knocked Down.

Полная формулировка: https://bloodbowlbase.ru/bb2025/core_rules/skills_and_traits/

## Изменения Gata League
- Во время собственной активации этого игрока, если при Block с его участием выпал результат Both Down, этот игрок не считается Knocked Down от этого результата. Вне собственной активации этого игрока Block не применяется.
```
Source `content/Gata/Skills and Traits/Skills/Dodge.md`:
```markdown
---
tags:
  - Active
  - Agility
---

## Rule summary
Once per turn this player may re-roll one Agility test made to Dodge. In base rules it also affects Stumble results; in Gata League that defensive part is handled by Evasive.

Full wording: https://bloodbowlbase.ru/bb2025/core_rules/skills_and_traits/

## Gata League change
- Once per turn, this player may reroll one failed Dodge test. Dodge no longer changes block dice results; that defensive effect is handled by Evasive.
```
Create `content/Gata-ru/Skills and Traits/Skills/Dodge.md`:
```markdown
---
tags:
  - Active
  - Agility
---

## Краткое описание
Раз за ход этот игрок может перебросить один тест Agility, сделанный для Dodge. В базовых правилах это также влияет на результаты Stumble; в Gata League эта защитная часть обрабатывается навыком Evasive.

Полная формулировка: https://bloodbowlbase.ru/bb2025/core_rules/skills_and_traits/

## Изменения Gata League
- Раз за ход этот игрок может перебросить один проваленный тест Dodge. Dodge больше не меняет результаты кубиков блока; этот защитный эффект обрабатывается навыком Evasive.
```
Note the recurring pattern: `tags:` values (`Active`, `General`, `Agility`) are category keywords — untranslated. The two headings `## Rule summary` → `## Краткое описание` and `## Gata League change` → `## Изменения Gata League` are the same in every skill file — reuse this exact translation for consistency across all 93 files. The `Full wording: <url>` line's label translates to `Полная формулировка: <url>` (same URL). Skill names referenced inline (`Dodge`, `Evasive`, `Block`, `Stumble`) stay in English — they're glossary terms.

- [ ] **Step 3: Translate the remaining 90 skill files plus `Skill Table.md`**

For every other file from the Step 1 listing: read the source, apply the exact same heading translations (`## Rule summary` → `## Краткое описание`, `## Gata League change` → `## Изменения Gata League`, `Full wording:` → `Полная формулировка:`), translate the rule-summary and Gata-League-change prose, keep every skill/trait/keyword name referenced inline in English, keep `tags:` frontmatter untranslated, write to the identically-named file under `content/Gata-ru/Skills and Traits/Skills/`.

For `content/Gata/Skills and Traits/Skill Table.md` (the master skill-category table used by `parseSkillGroups`): translate only the table's descriptive header text if any exists outside the table itself; the table cells are skill names (glossary terms — e.g. column headers `Agility`, `Devious`, `General`, `Mutation`, `Passing`, `Strength` are the six skill-category keywords used by `skillCategories` in `scripts/build-data.mjs:38` — keep these exactly as-is, since they're matched verbatim by that array) and must stay byte-identical to the English version's table structure and cell values (only reorder/relabel nothing — this file is structurally load-bearing, not descriptive prose).

- [ ] **Step 4: Rebuild and verify**

Run: `npm run build && npm run i18n:check`. Expected: passes, 93+1 new files reflected in the page count parity between locales.

- [ ] **Step 5: Spot-check 6 files (across different tag categories) against the glossary.**

- [ ] **Step 6: Commit**

```bash
git add "content/Gata-ru/Skills and Traits/Skills" "content/Gata-ru/Skills and Traits/Skill Table.md"
git commit -m "Translate Skills content to Russian"
```

---

### Task 12: Translate content — Traits

**Files:**
- Create all 38 files under `content/Gata-ru/Skills and Traits/Traits/` (get the authoritative list by running `ls "content/Gata/Skills and Traits/Traits"` before starting)

**Interfaces:**
- Consumes: `docs/i18n-glossary.md`, `npm run i18n:check`.

- [ ] **Step 1: Get the exact file list**

Run: `ls "content/Gata/Skills and Traits/Traits" | sort`. This is your checklist.

- [ ] **Step 2: Worked example**

Source (first file alphabetically, confirmed against the repo — verify the exact current name and content with `ls` and `cat` before translating, since trait file names may shift as the roster changes):
```markdown
---
tags:
  - Trait
---

## Rule summary
Before throwing a team-mate, this player must roll. On 2+ continue normally; on 1, roll again. The second roll either makes the team-mate squirm free for a fumbled throw or be eaten and removed, causing a Turnover if they had the ball.

Full wording: https://bloodbowlbase.ru/bb2025/core_rules/skills_and_traits/
```
Translate using the same heading convention established in Task 11 (`## Rule summary` → `## Краткое описание`, `Full wording:` → `Полная формулировка:`):
```markdown
---
tags:
  - Trait
---

## Краткое описание
Перед тем как бросить союзника, этот игрок должен сделать бросок. На 2+ продолжайте как обычно; на 1 — сделайте ещё один бросок. Второй бросок либо позволяет союзнику вырваться (бросок считается неудачным), либо союзника съедают и убирают с поля, что вызывает Turnover, если у него был мяч.

Полная формулировка: https://bloodbowlbase.ru/bb2025/core_rules/skills_and_traits/
```
(`tags: Trait` stays in English — category keyword. `Turnover` stays in English — Blood Bowl rule keyword.)

- [ ] **Step 3: Translate the remaining 37 trait files**

Same process as Task 11 Step 3, applied to every file from the Step 1 listing, writing into `content/Gata-ru/Skills and Traits/Traits/`. Some traits won't have a `## Gata League change` section (base-rules traits with no house-rule change) — only include that heading in the translated file if the source has it.

- [ ] **Step 4: Rebuild and verify**

Run: `npm run build && npm run i18n:check`. Expected: passes.

- [ ] **Step 5: Spot-check 4 files against the glossary.**

- [ ] **Step 6: Commit**

```bash
git add "content/Gata-ru/Skills and Traits/Traits"
git commit -m "Translate Traits content to Russian"
```

---

### Task 13: Translate content — Star Players

**Files:**
- Create `content/Gata-ru/Star Players/_index.json` (copied verbatim, unchanged — it's a filename manifest, not prose)
- Create all 91 `.md` files under `content/Gata-ru/Star Players/` (get the authoritative list by running `ls "content/Gata/Star Players"` before starting)

**Interfaces:**
- Consumes: `docs/i18n-glossary.md`, `npm run i18n:check`, the corrected `extractStarPlayerMeta` regex from Task 1 (the `**Доступность:**`/`**Цена:**`/`**Команды:**` labels).

- [ ] **Step 1: Get the exact file list and copy the index manifest**

Run:
```bash
ls "content/Gata/Star Players" | sort
mkdir -p "content/Gata-ru/Star Players"
cp "content/Gata/Star Players/_index.json" "content/Gata-ru/Star Players/_index.json"
```
`walk()` in `scripts/build-data.mjs` (line 490-502) reads this manifest to filter which files it processes for the Star Players folder — it must exist, unchanged, in the RU vault too.

- [ ] **Step 2: Worked example — translate `Asperon Thorn.md`**

Source `content/Gata/Star Players/Asperon Thorn.md` (confirmed against the repo):
```markdown
---
tags:
  - Star Player
---


**Name:** Asperon Thorn
**Availability:** -
**Cost:** 170k

| MA | ST | AG | PA | AR | Cost | Skills | Keywords |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | 3 | 2+ | 2+ | 9+ | 170k | [[Hail Mary Pass]], [[On the Ball]], [[Pass]], [[Safe Pass]], [[Sure Hands]], [[Loner (4+)]] |  |

**Special Ability:** Precision Pass: Once per game, when a Pass Action is performed by Asperon, no modifiers are applied when determening the range of the Pass.
```
Create `content/Gata-ru/Star Players/Asperon Thorn.md`:
```markdown
---
tags:
  - Star Player
---


**Имя:** Asperon Thorn
**Доступность:** -
**Цена:** 170k

| MA | ST | AG | PA | AR | Cost | Skills | Keywords |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | 3 | 2+ | 2+ | 9+ | 170k | [[Hail Mary Pass]], [[On the Ball]], [[Pass]], [[Safe Pass]], [[Sure Hands]], [[Loner (4+)]] |  |

**Персональная способность:** Precision Pass: раз за игру, когда Asperon выполняет Pass Action, дальность Pass определяется без модификаторов.
```
Note: the star player's own name (`Asperon Thorn`) stays in English even after `**Имя:**` — it's a glossary term. The table header row and all skill/keyword cell values stay exactly as in the source (table structure and cell contents are load-bearing — untranslated). Only the bold-label text and the special-ability description prose are translated. The `**Доступность:**`/`**Цена:**` labels must be exactly these strings (per Task 7's glossary table) for `extractStarPlayerMeta` to parse them.

- [ ] **Step 3: Translate the remaining 90 star player files**

For every other file from the Step 1 listing: read the source, apply `**Имя:**`/`**Доступность:**`/`**Цена:**`/`**Команды:**` (if present)/`**Персональная способность:**` labels exactly as shown, translate only the special-ability description prose (keep every skill name, keyword, and other star player/team name referenced inside that prose in English), leave the stat table and its cell values untouched, write to the identically-named file under `content/Gata-ru/Star Players/`.

- [ ] **Step 4: Rebuild and verify**

Run: `npm run build && npm run i18n:check`. Expected: passes, and additionally spot-check that metadata parsing worked:
```bash
node -e "
const data = JSON.parse(require('fs').readFileSync('public/data.ru.json', 'utf8'));
const asperon = data.starPlayers.find((p) => p.title === 'Asperon Thorn');
console.log(asperon.starPlayer);
"
```
Expected output includes `availability: '-'` and `cost: '170'` (or however `normalizeCost` formats it) — matching the English build's parsed values, confirming the Russian bold labels were recognized.

- [ ] **Step 5: Spot-check 6 files against the glossary.**

- [ ] **Step 6: Commit**

```bash
git add "content/Gata-ru/Star Players"
git commit -m "Translate Star Players content to Russian"
```

---

### Task 14: Translate content — Teams

**Files:**
- Create all 37 files under `content/Gata-ru/Teams/` (get the authoritative list by running `ls "content/Gata/Teams"` before starting)

**Interfaces:**
- Consumes: `docs/i18n-glossary.md`, `npm run i18n:check`, the corrected `extractTeamMeta` regex from Task 1.

Team files are almost entirely structured data (roster tables) with 4 short metadata lines — this is the lightest-touch content task.

- [ ] **Step 1: Get the exact file list**

Run: `ls "content/Gata/Teams" | sort`. This is your checklist.

- [ ] **Step 2: Worked example — translate `Amazon.md`**

Source `content/Gata/Teams/Amazon.md` (confirmed against the repo):
```markdown
| Qty | Position | MA | ST | AG | PA | AR | Skills | Primary | Secondary | Cost | Tags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0-16 | Eagle Warrior Linewoman | 6 | 3 | 3+ | 4+ | 8+ | [[Evasive]] | G | A S | 50K | Human, Lineman |
| 0-2 | Python Warrior Thrower | 6 | 3 | 3+ | 3+ | 8+ | [[Evasive]], [[On the Ball]], [[Pass]], [[Safe Pass]] | G P | A S | 80K | Human, Thrower |
| 0-2 | Piranha Warrior Blitzer | 7 | 3 | 3+ | 5+ | 8+ | [[Evasive]], [[Hit and Run]], [[Jump Up]] | A G | S | 70K | Human, Blitzer |
| 0-2 | Jaguar Warrior Blocker | 6 | 4 | 3+ | 5+ | 9+ | [[Evasive]], [[Defensive]] | G S | A | 130K | Human, Blocker |

**Rerolls:** 60K
**Apothecary:** Apothecary: Available
**League:** Tier 1
**Special Rules:** Lustrian Superleague
```
Create `content/Gata-ru/Teams/Amazon.md`:
```markdown
| Qty | Position | MA | ST | AG | PA | AR | Skills | Primary | Secondary | Cost | Tags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0-16 | Eagle Warrior Linewoman | 6 | 3 | 3+ | 4+ | 8+ | [[Evasive]] | G | A S | 50K | Human, Lineman |
| 0-2 | Python Warrior Thrower | 6 | 3 | 3+ | 3+ | 8+ | [[Evasive]], [[On the Ball]], [[Pass]], [[Safe Pass]] | G P | A S | 80K | Human, Thrower |
| 0-2 | Piranha Warrior Blitzer | 7 | 3 | 3+ | 5+ | 8+ | [[Evasive]], [[Hit and Run]], [[Jump Up]] | A G | S | 70K | Human, Blitzer |
| 0-2 | Jaguar Warrior Blocker | 6 | 4 | 3+ | 5+ | 9+ | [[Evasive]], [[Defensive]] | G S | A | 130K | Human, Blocker |

**Перебросы:** 60K
**Апотекарий:** Есть
**Лига:** Дивизион 1
**Специальные правила:** Lustrian Superleague
```
Notes:
- The roster table (`Qty`/position names/stats/skills/`Primary`/`Secondary`/`Cost`/`Tags` cell values like "Human, Lineman") stays completely untouched — every cell is either a number, a stat shorthand, or a glossary term (position name, skill name, race/team tag).
- `**Апотекарий:** Есть` — the source's "Apothecary: Available" is oddly redundant (repeats the label); translate the *meaning* ("available") naturally rather than literally repeating the label — "Есть" ("present/available") reads correctly in context. If a team's source says "Apothecary: None"/absent, use "Нет".
- `**Лига:** Дивизион 1` — "Tier 1" is a league-tier UI-ish label describing competitive tier, not a proper name; translate it ("Division 1"/"Tier 1" → "Дивизион 1") unless the source uses a proper league name (some teams may reference a named league — check `content/Gata/General Information/Leagues.md`, translated in Task 9, for whether tier labels used there are proper names; if so, reuse that exact translation for consistency instead of retranslating independently).
- `**Специальные правила:** Lustrian Superleague` — this is a special rule's proper name (glossary term, matches its entry translated in Task 9's `Special Rules.md`) — kept in English, unchanged.

- [ ] **Step 3: Translate the remaining 36 team files**

For every other file from the Step 1 listing: keep the roster table byte-identical (only structured data, no prose to translate), translate the 4 bold-label lines using the exact `**Перебросы:**`/`**Апотекарий:**`/`**Лига:**`/`**Специальные правила:**` labels from Task 7's glossary table, translate only the short status words after `Apothecary`/`League` naturally (not the special-rule name itself), write to the identically-named file under `content/Gata-ru/Teams/`.

- [ ] **Step 4: Rebuild and verify**

Run: `npm run build && npm run i18n:check`. Expected: passes. Additionally spot-check metadata parsing:
```bash
node -e "
const data = JSON.parse(require('fs').readFileSync('public/data.ru.json', 'utf8'));
const amazon = data.teams.find((p) => p.title === 'Amazon');
console.log(amazon.team.meta);
"
```
Expected output includes non-empty `rerolls`, `apothecary`, `league`, `specialRules` fields (confirming the Russian bold labels were recognized by `extractTeamMeta`).

- [ ] **Step 5: Spot-check 6 files against the glossary.**

- [ ] **Step 6: Commit**

```bash
git add content/Gata-ru/Teams
git commit -m "Translate Teams content to Russian"
```

---

### Task 15: Final QA pass

**Files:** none (verification only, plus the `dist`/build-site inlining update deferred here since it only matters for the static-preview path).

**Interfaces:**
- Consumes: everything from Tasks 1-14.

- [ ] **Step 1: Update `scripts/build-site.mjs` for dual-locale static inlining**

Find, at the end of `scripts/build-site.mjs`:
```js
const dataJson = (await fs.readFile(path.join(rootDir, "public", "data.json"), "utf8"))
  .replace(/</g, "\\u003c");
const localPreviewHtml = indexHtml.replace(
  '<script type="module" src="src/app.js?v=gata-52"></script>',
  `<script>window.__REFERENCE_DATA__ = ${dataJson};</script>\n    <script src="src/app.js?v=gata-52"></script>`,
);
await fs.writeFile(path.join(distDir, "local-preview.html"), localPreviewHtml);
```
Replace with:
```js
const enDataJson = (await fs.readFile(path.join(rootDir, "public", "data.en.json"), "utf8"))
  .replace(/</g, "\\u003c");
const ruDataJson = (await fs.readFile(path.join(rootDir, "public", "data.ru.json"), "utf8"))
  .replace(/</g, "\\u003c");
const localPreviewHtml = indexHtml.replace(
  '<script type="module" src="src/app.js?v=gata-52"></script>',
  `<script>window.__REFERENCE_DATA__ = { en: ${enDataJson}, ru: ${ruDataJson} };</script>\n    <script src="src/app.js?v=gata-52"></script>`,
);
await fs.writeFile(path.join(distDir, "local-preview.html"), localPreviewHtml);
```
This matches Task 2's `loadLocaleData()`, which reads `window.__REFERENCE_DATA__[locale]` when present. (`copyDir(path.join(rootDir, "public"), path.join(distDir, "public"))`, a few lines above and unchanged, already copies `data.en.json`/`data.ru.json`/`data.json` into `dist/public/` since Task 1 writes all three there.)

- [ ] **Step 2: Full rebuild**

Run: `npm run build`. Expected: no errors, `public/data.en.json`, `public/data.ru.json`, `public/data.json`, and `dist/local-preview.html` all regenerate.

- [ ] **Step 3: Run the glossary check one final time**

Run: `npm run i18n:check`. Expected: passes with the full page count (299, or whatever the current total is).

- [ ] **Step 4: Full manual walkthrough in English**

Run `npm run dev`. With locale forced to English (`localStorage.setItem("gata-league-locale", "en")` then reload if needed), click through every nav item, open at least 2 detail pages per section, use the builder to add a player, and confirm nothing regressed from before this project started.

- [ ] **Step 5: Full manual walkthrough in Russian**

Force `localStorage.setItem("gata-league-locale", "ru")`, reload. Repeat the same walkthrough. Confirm:
- All nav/chrome/builder UI is in Russian.
- All rule/inducement/skill/trait/star-player/team descriptive text is in Russian.
- Every team name, race name, position name, skill/trait name, star player name, inducement/special-rule name, and stat abbreviation (MA/ST/AG/PA/AV/SPP/TV/GP/CAS) is still in English.
- The global search box finds results when searching in Russian (e.g. search a Russian word that appears in a translated rule) and in English (e.g. search "Block").
- Toggling locale mid-session on a detail page keeps you on that same page, just retranslated.

- [ ] **Step 6: Confirm `content/7ZBBL` is untouched**

Run: `git status content/7ZBBL` — expected: no changes reported anywhere in this project's history touch that folder.

- [ ] **Step 7: Commit**

```bash
git add scripts/build-site.mjs
git commit -m "Inline both locales in the static build-site output; final i18n QA pass"
```
