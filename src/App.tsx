import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  Heart,
  Moon,
  Search,
  SlidersHorizontal,
  Sun,
  X,
} from "lucide-react";
import { loadCatalog } from "./data/client";
import type { Manifest, Perfume } from "./data/contracts";
import { PerfumeCard } from "./features/catalog/PerfumeCard";
import { FilterChips, Filters } from "./features/catalog/Filters";
import {
  emptyQuery,
  filterKeys,
  selectPerfumes,
  type CatalogQuery,
} from "./features/catalog/query";
import { PerfumeDetails } from "./features/details/PerfumeDetails";
import {
  FAVORITES_KEY,
  readFavorites,
  saveFavorites,
} from "./features/favorites/storage";
import { navigate, useRoute } from "./shared/useRoute";
import { ErrorState, LoadingCards } from "./shared/ui";

function initialTheme() {
  try {
    const saved = localStorage.getItem("shobi-appearance");
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    /* Browser storage can be unavailable. */
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export default function App() {
  const { detailId, query } = useRoute();
  const [catalog, setCatalog] = useState<{
    manifest: Manifest;
    perfumes: Perfume[];
  } | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [favorites, setFavorites] = useState(readFavorites);
  const [storageWarning, setStorageWarning] = useState(false);
  const [theme, setTheme] = useState(initialTheme);
  const [search, setSearch] = useState(query.q);
  const [limit, setLimit] = useState(24);
  const dialog = useRef<HTMLDialogElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const lastDetail = useRef<string | null>(null);
  const browseScroll = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    loadCatalog(controller.signal)
      .then(setCatalog)
      .catch((e) => {
        if (e.name !== "AbortError") setError(true);
      });
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("shobi-appearance", theme);
    } catch {
      /* Theme still works for this visit. */
    }
  }, [theme]);
  useEffect(() => {
    setSearch(query.q);
  }, [query.q]);
  useEffect(() => {
    if (search === query.q) return;
    const timer = window.setTimeout(
      () => navigate({ ...query, q: search }, undefined, true),
      180,
    );
    return () => window.clearTimeout(timer);
  }, [
    search,
    query.q,
    query.sort,
    query.saved,
    JSON.stringify(filterKeys.map((k) => query[k])),
  ]);
  useEffect(() => {
    const sync = (e: StorageEvent) => {
      if (e.key === FAVORITES_KEY) setFavorites(readFavorites());
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);
  useEffect(() => {
    setLimit(24);
  }, [JSON.stringify(query)]);
  useEffect(() => {
    if (detailId && !lastDetail.current) {
      browseScroll.current = window.scrollY;
      window.scrollTo(0, 0);
    }
    if (!detailId && lastDetail.current) {
      document.title = "Shobi Perfume Finder — Find your next fragrance";
      const previousId = lastDetail.current;
      requestAnimationFrame(() => {
        window.scrollTo(0, browseScroll.current);
        document
          .getElementById(`perfume-card-${previousId}`)
          ?.querySelector<HTMLAnchorElement>(".card-copy h3 a")
          ?.focus({ preventScroll: true });
      });
    }
    lastDetail.current = detailId;
  }, [detailId]);

  const change = (patch: Partial<CatalogQuery>) =>
    navigate({ ...query, q: search, ...patch });
  const canonicalFavorites = useMemo(() => {
    const result = new Set(favorites);
    catalog?.perfumes.forEach((p) => {
      if (p.aliases.some((a) => favorites.has(a))) result.add(p.code);
    });
    return result;
  }, [favorites, catalog]);
  const favoriteCount = catalog
    ? catalog.perfumes.filter((p) => canonicalFavorites.has(p.code)).length
    : favorites.size;
  const toggle = (code: string) => {
    const next = new Set(favorites);
    const perfume = catalog?.perfumes.find((p) => p.code === code);
    if (canonicalFavorites.has(code)) {
      next.delete(code);
      perfume?.aliases.forEach((a) => next.delete(a));
    } else next.add(code);
    setFavorites(next);
    setStorageWarning(!saveFavorites(next));
  };
  const results = useMemo(
    () =>
      catalog
        ? selectPerfumes(catalog.perfumes, query, canonicalFavorites)
        : [],
    [catalog, JSON.stringify(query), canonicalFavorites],
  );
  const reset = () => {
    setSearch("");
    navigate({ ...emptyQuery(), saved: query.saved });
  };

  return (
    <>
      <a
        href="#main"
        className="skip-link"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main")?.focus();
          document.getElementById("main")?.scrollIntoView();
        }}
      >
        Skip to content
      </a>
      <header className="site-header">
        <div className="header-inner">
          <a
            className="wordmark"
            href="#/"
            aria-label="Shobi Perfume Finder home"
          >
            <span>
              Shobi
              <span className="wordmark-subtitle">Perfume Finder</span>
            </span>
          </a>
          <nav aria-label="Main navigation">
            <a className={!query.saved && !detailId ? "active" : ""} href="#/">
              Discover
            </a>
            <button
              className={query.saved ? "nav-favorites active" : "nav-favorites"}
              onClick={() => {
                setSearch("");
                navigate({ ...emptyQuery(), saved: true });
              }}
            >
              <Heart size={16} />
              Favorites
              {favoriteCount > 0 && (
                <span className="nav-count">{favoriteCount}</span>
              )}
            </button>
          </nav>
          <button
            className="icon-button theme-toggle"
            onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} appearance`}
          >
            {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
          </button>
        </div>
      </header>
      {storageWarning && (
        <p className="storage-warning" role="status">
          Favorites are saved for this visit. Your browser could not store them
          for next time.
        </p>
      )}
      {detailId && catalog ? (
        <PerfumeDetails
          key={detailId}
          id={detailId}
          manifest={catalog.manifest}
          query={query}
          favorites={canonicalFavorites}
          toggle={toggle}
        />
      ) : (
        <>
          <main className="catalog-layout" id="main" tabIndex={-1}>
            <aside className="desktop-filters" aria-label="Fragrance filters">
              {catalog && (
                <Filters
                  perfumes={catalog.perfumes}
                  query={query}
                  change={change}
                />
              )}
            </aside>
            <section className="catalog-results" aria-label="Fragrance results">
              <div className="main-search catalog-search">
                <Search size={21} strokeWidth={1.6} />
                <label className="sr-only" htmlFor="fragrance-search">
                  Search fragrances
                </label>
                <input
                  ref={searchInput}
                  id="fragrance-search"
                  type="search"
                  placeholder="Search perfume, brand or Shobi code"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <div className="results-toolbar">
                <div>
                  <h1>
                    {query.saved ? "Favorites" : "Perfume catalog"}
                    <span aria-live="polite">
                      {catalog ? results.length.toLocaleString() : "…"}
                    </span>
                  </h1>
                </div>
                <div className="results-controls">
                  <button
                    className="button secondary mobile-filter-button"
                    onClick={() => dialog.current?.showModal()}
                  >
                    <SlidersHorizontal size={16} />
                    Filters
                  </button>
                  <label className="sort-label">
                    Sort by
                    <select
                      aria-label="Sort fragrances"
                      value={query.sort}
                      onChange={(e) =>
                        change({ sort: e.target.value as CatalogQuery["sort"] })
                      }
                    >
                      <option value="brand">Brand, A–Z</option>
                      <option value="name">Name, A–Z</option>
                      <option value="best">Official best sellers</option>
                    </select>
                  </label>
                </div>
              </div>
              <FilterChips query={query} change={change} />
              {error ? (
                <ErrorState
                  message="The fragrance library could not be loaded. Check your connection and try again."
                  retry={() => setAttempt((a) => a + 1)}
                />
              ) : !catalog ? (
                <LoadingCards />
              ) : results.length ? (
                <>
                  <div className="card-grid">
                    {results.slice(0, limit).map((p) => (
                      <PerfumeCard
                        key={p.id}
                        perfume={p}
                        query={query}
                        saved={canonicalFavorites.has(p.code)}
                        toggleFavorite={() => toggle(p.code)}
                      />
                    ))}
                  </div>
                  <div className="load-more">
                    <p>
                      Showing {Math.min(limit, results.length)} of{" "}
                      {results.length.toLocaleString()} fragrances
                    </p>
                    {limit < results.length && (
                      <button
                        className="button secondary"
                        onClick={() => setLimit((l) => l + 24)}
                      >
                        Explore more
                        <ArrowRight size={16} />
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <div className="empty-state">
                  <Heart size={36} strokeWidth={1} />
                  <h2>
                    {query.saved && !favoriteCount
                      ? "Make room for a favorite"
                      : "A different note, perhaps?"}
                  </h2>
                  <p>
                    {query.saved && !favoriteCount
                      ? "Tap the heart on a fragrance to keep it here for later."
                      : "No fragrances match this combination. Try a different search or remove a filter."}
                  </p>
                  <button
                    className="button primary"
                    onClick={
                      query.saved && !favoriteCount
                        ? () => navigate(emptyQuery())
                        : reset
                    }
                  >
                    {query.saved && !favoriteCount
                      ? "Explore fragrances"
                      : "Clear search & filters"}
                  </button>
                </div>
              )}
            </section>
          </main>
          <dialog
            ref={dialog}
            className="mobile-filter-sheet"
            aria-labelledby="mobile-filter-title"
            onClick={(e) => {
              if (e.target === e.currentTarget) dialog.current?.close();
            }}
          >
            <div className="sheet-content">
              <div className="sheet-heading">
                <h2 id="mobile-filter-title">Find your fragrance</h2>
                <button
                  className="icon-button"
                  autoFocus
                  aria-label="Close filters"
                  onClick={() => dialog.current?.close()}
                >
                  <X size={21} />
                </button>
              </div>
              {catalog && (
                <Filters
                  perfumes={catalog.perfumes}
                  query={query}
                  change={change}
                />
              )}
              <div className="sheet-footer">
                <button
                  className="button primary"
                  onClick={() => dialog.current?.close()}
                >
                  Show {results.length.toLocaleString()} fragrances
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </dialog>
        </>
      )}
      <footer className="site-footer">
        <div>
          <a className="footer-wordmark" href="#/">
            Shobi Perfume Finder
          </a>
        </div>
        <p>
          Independent discovery project. Not affiliated with Shobi or the
          original brands.
          <br />
          Inspired by smellyCat-deep, with catalog work by MarvvRed. GPL-3.0.
        </p>
      </footer>
    </>
  );
}
