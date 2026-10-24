import { Droplets } from "lucide-react";
import type { Profile } from "../../data/contracts";
import { recommendBoost } from "./rules";

export function BoostGuide({ profile }: { profile: Profile }) {
  const result = recommendBoost(profile.accords, profile.evidence.accords);
  return (
    <section className="boost-guide" aria-labelledby="boost-heading">
      <div className="section-label">
        <Droplets size={19} />
        <span>THE FINISHING TOUCH</span>
      </div>
      <h2 id="boost-heading">Essence Boost Guide</h2>
      {result.available ? (
        <>
          <p>
            Guidance for a{" "}
            <strong>{result.classification.toLowerCase()}</strong> fragrance,
            based on its {result.matchedAccords.join(", ")} accords.
          </p>
          <div className="boost-amounts">
            {["30ml", "50ml", "100ml"].map((size, i) => (
              <div key={size}>
                <span>{size} bottle</span>
                <strong>+{result.amounts[i]}</strong>
                <small>extra essence</small>
              </div>
            ))}
          </div>
        </>
      ) : (
        <>
          <p className="boost-unavailable">
            Not enough information for a recommendation.
          </p>
        </>
      )}
    </section>
  );
}
