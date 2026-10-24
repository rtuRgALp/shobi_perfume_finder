import type { Evidence } from "../../data/contracts";
import rules from "../../../contracts/boost-rules.v1.json";

export const BOOST_RULE_VERSION = rules.version;
const vocabulary: Record<string, string> = rules.vocabulary;
const heavy = new Set(rules.heavy);
const light = new Set(rules.light);
export type BoostResult =
  | { available: false; ruleVersion: string }
  | {
      available: true;
      ruleVersion: string;
      classification: "Heavy / gourmand" | "Fresh / light";
      matchedAccords: string[];
      amounts: [string, string, string];
      source: string;
      provenance: "verified" | "provider";
    };
export function recommendBoost(
  accords: string[],
  evidence?: Evidence,
): BoostResult {
  const unavailable = {
    available: false as const,
    ruleVersion: BOOST_RULE_VERSION,
  };
  if (
    (evidence?.status !== "verified" && evidence?.status !== "provider") ||
    !evidence.source
  )
    return unavailable;
  const recognized = accords
    .map((a) => ({
      original: a,
      canonical: vocabulary[a.trim().toLowerCase()],
    }))
    .filter((a) => a.canonical);
  const isHeavy = recognized.some((a) => heavy.has(a.canonical));
  const matched = recognized.filter((a) =>
    (isHeavy ? heavy : light).has(a.canonical),
  );
  if (!matched.length) return unavailable;
  return {
    available: true,
    ruleVersion: BOOST_RULE_VERSION,
    classification: isHeavy ? "Heavy / gourmand" : "Fresh / light",
    matchedAccords: matched.map((a) => a.original),
    amounts: (isHeavy ? rules.amounts.heavy : rules.amounts.light) as [
      string,
      string,
      string,
    ],
    source: evidence.source,
    provenance: evidence.status,
  };
}
