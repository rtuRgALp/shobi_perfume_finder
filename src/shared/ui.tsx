import { useState } from "react";
import { FlaskConical, ArrowUpRight, Heart } from "lucide-react";
import { publicUrl } from "../data/client";

export function BottleImage({
  src,
  name,
  className = "",
}: {
  src: string | null;
  name: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`bottle-image ${className}`}>
      {src && !failed ? (
        <img
          src={publicUrl(src)}
          alt={`${name} original perfume bottle`}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="bottle-placeholder">
          <FlaskConical size={40} strokeWidth={1} />
          <span>Image unavailable</span>
        </div>
      )}
    </div>
  );
}
export function FavoriteButton({
  saved,
  onClick,
  name,
  compact = false,
}: {
  saved: boolean;
  onClick: () => void;
  name: string;
  compact?: boolean;
}) {
  return (
    <button
      className={compact ? "favorite-icon icon-button" : "button secondary"}
      aria-label={`${saved ? "Remove" : "Save"} ${name} ${saved ? "from" : "to"} favorites`}
      aria-pressed={saved}
      onClick={onClick}
    >
      <Heart size={18} fill={saved ? "currentColor" : "none"} />
      {!compact && (saved ? "Saved to favorites" : "Save fragrance")}
    </button>
  );
}
export function ExternalLink({
  href,
  children,
  className = "",
}: {
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <a
      className={className}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
      <ArrowUpRight size={15} aria-hidden="true" />
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="empty-state" role="alert">
      <FlaskConical size={36} strokeWidth={1} />
      <h2>A little pause in discovery</h2>
      <p>{message}</p>
      {retry && (
        <button className="button primary" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function LoadingCards() {
  return (
    <div className="card-grid" aria-label="Loading fragrances" aria-busy="true">
      {Array.from({ length: 8 }, (_, i) => (
        <div className="skeleton-card" key={i}>
          <div />
          <span />
          <span />
        </div>
      ))}
    </div>
  );
}
