import { ArrowUpRight } from "lucide-react";
import type { Perfume } from "../../data/contracts";
import { detailHref } from "../../shared/useRoute";
import { BottleImage, FavoriteButton } from "../../shared/ui";
import { type CatalogQuery } from "./query";

export function PerfumeCard({
  perfume: p,
  query,
  saved,
  toggleFavorite,
}: {
  perfume: Perfume;
  query: CatalogQuery;
  saved: boolean;
  toggleFavorite: () => void;
}) {
  const href = detailHref(p.id, query);
  return (
    <article className="perfume-card" id={`perfume-card-${p.id}`}>
      <div className="card-image-wrap">
        <a
          href={href}
          aria-label={`Explore ${p.name} by ${p.brand}`}
          tabIndex={-1}
        >
          <BottleImage key={p.image} src={p.image} name={p.name} />
        </a>
        <FavoriteButton
          compact
          saved={saved}
          onClick={toggleFavorite}
          name={p.name}
        />
      </div>
      <div className="card-copy">
        <p className="eyebrow card-brand">{p.brand}</p>
        <h3>
          <a href={href}>{p.name}</a>
        </h3>
        <div className="card-meta">
          <span className="product-code">{p.code}</span>
          {p.gender && (
            <>
              <span className="meta-dot">·</span>
              <span>
                {p.gender === "masculine"
                  ? "Masculine"
                  : p.gender === "feminine"
                    ? "Feminine"
                    : "Unisex"}
              </span>
            </>
          )}
        </div>
        <div className="card-notes">
          {p.mainNotes.length ? (
            p.mainNotes
              .slice(0, 3)
              .map((n) => <span key={n.name}>{n.name}</span>)
          ) : (
            <span className="muted">Notes not yet available</span>
          )}
        </div>
        <a
          href={href}
          className="card-explore"
          aria-label={`View details for ${p.name}`}
        >
          Discover fragrance <ArrowUpRight size={15} aria-hidden="true" />
        </a>
      </div>
    </article>
  );
}
