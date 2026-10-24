import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { loadProfile, publicUrl } from "../../data/client";
import type { Manifest, Profile } from "../../data/contracts";
import { serializeQuery, type CatalogQuery } from "../catalog/query";
import { BoostGuide } from "../boost/BoostGuide";
import {
  BottleImage,
  ErrorState,
  ExternalLink,
  FavoriteButton,
} from "../../shared/ui";

function formatMetric(metric: Profile["longevity"] | Profile["rating"]) {
  if (!metric) return "Not available";
  if ("label" in metric) return metric.label;
  const scale = metric.scale.replace(/\s*\([^)]*\)/g, "");
  return `${metric.value} (${scale})`;
}

export function PerfumeDetails({
  id,
  manifest,
  query,
  favorites,
  toggle,
}: {
  id: string;
  manifest: Manifest;
  query: CatalogQuery;
  favorites: Set<string>;
  toggle: (code: string) => void;
}) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setProfile(null);
    setError(false);
    loadProfile(id, manifest, controller.signal)
      .then(setProfile)
      .catch((e) => {
        if (e.name !== "AbortError") setError(true);
      });
    return () => controller.abort();
  }, [id, manifest, attempt]);
  useEffect(() => {
    if (profile) {
      document.title = `${profile.name} by ${profile.brand} — Shobi Perfume Finder`;
      document.getElementById("perfume-title")?.focus();
    }
  }, [profile]);
  return (
    <main className="detail-page" id="main" tabIndex={-1}>
      <a className="back-link" href={"#/" + serializeQuery(query)}>
        <ArrowLeft size={17} />
        Back to {query.saved ? "favorites" : "discovery"}
      </a>
      {error ? (
        <ErrorState
          message="This perfume’s details could not be loaded. Your library is still available."
          retry={() => setAttempt((a) => a + 1)}
        />
      ) : !profile ? (
        <div className="detail-loading" role="status">
          Opening the fragrance profile…
        </div>
      ) : (
        <>
          <div className="detail-top">
            <BottleImage
              key={profile.image}
              src={profile.image}
              name={profile.name}
              className="detail-image"
            />
            <div className="detail-intro">
              <p className="eyebrow">INSPIRED BY · {profile.brand}</p>
              <h1 id="perfume-title" tabIndex={-1}>
                {profile.name}
              </h1>
              {profile.edition && <p className="muted">{profile.edition}</p>}
              <p className="detail-code">
                SHOBI <span>{profile.listings[0].code}</span>
              </p>
              <div className="detail-tags">
                {[profile.gender, ...profile.seasons]
                  .filter(Boolean)
                  .map((t) => (
                    <span key={t}>{t}</span>
                  ))}
              </div>

              {profile.description && (
                <p className="detail-description">{profile.description}</p>
              )}

              <div className="detail-actions">
                <ExternalLink
                  className="button primary"
                  href={profile.listings[0].url}
                >
                  View on Shobi
                </ExternalLink>
                <FavoriteButton
                  saved={favorites.has(profile.listings[0].code)}
                  onClick={() => toggle(profile.listings[0].code)}
                  name={profile.name}
                />
              </div>
              {profile.fragranticaUrl && (
                <ExternalLink
                  className="subtle-link"
                  href={profile.fragranticaUrl}
                >
                  Read about the original on Fragrantica
                </ExternalLink>
              )}
            </div>
          </div>
          <div className="detail-sections">
            <div>
              <section className="profile-section">
                <p className="eyebrow">THE SCENT, AT A GLANCE</p>
                <h2>Main Notes</h2>
                {profile.mainNotes.length ? (
                  <div className="detail-notes">
                    {profile.mainNotes.map((n) => (
                      <div key={n.name}>
                        {n.icon && (
                          <img
                            src={publicUrl(n.icon)}
                            alt=""
                            loading="lazy"
                            onError={(e) => {
                              e.currentTarget.style.visibility = "hidden";
                            }}
                          />
                        )}
                        <span>{n.name}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="missing-field">
                    Main Notes are not yet available.
                  </p>
                )}
              </section>
              <section className="profile-section">
                <h2>Accords</h2>
                {profile.accords.length ? (
                  <div className="accord-list">
                    {profile.accords.map((a) => (
                      <span key={a}>{a}</span>
                    ))}
                  </div>
                ) : (
                  <p className="missing-field">
                    Accords are not yet available.
                  </p>
                )}
              </section>
              <section className="profile-section">
                <h2>Note pyramid</h2>
                <p className="muted">Top, heart and base notes.</p>
                {(["top", "heart", "base"] as const).map((level) => (
                  <div className="pyramid-row" key={level}>
                    <strong>
                      {level === "heart"
                        ? "Heart"
                        : level === "top"
                          ? "Top"
                          : "Base"}
                    </strong>
                    <span>
                      {profile.pyramid[level].join(" · ") || "Not available"}
                    </span>
                  </div>
                ))}
              </section>
            </div>
            <div>
              <BoostGuide profile={profile} />
              <section className="profile-section performance-section">
                <h2>Original perfume profile</h2>
                {(["rating", "longevity", "sillage"] as const).map((key) => (
                  <div className="metric" key={key}>
                    <span>
                      {key === "rating"
                        ? "Rating"
                        : key === "longevity"
                          ? "Longevity"
                          : "Sillage"}
                    </span>
                    <strong>{formatMetric(profile[key])}</strong>
                    {profile[key]?.votes != null && (
                      <small>
                        {profile[key].votes?.toLocaleString()} votes
                      </small>
                    )}
                  </div>
                ))}
              </section>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
