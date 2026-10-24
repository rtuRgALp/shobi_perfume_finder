import { useId, useState } from "react";
import { ChevronDown, Search, X } from "lucide-react";
import type { Perfume } from "../../data/contracts";
import {
  filterKeys,
  normalize,
  values,
  type CatalogQuery,
  type FilterKey,
} from "./query";

const labels: Record<FilterKey, string> = {
  brand: "Brand",
  gender: "Fragrance style",
  season: "Season",
  note: "Main Notes",
  accord: "Accords",
};
export const labelValue = (value: string) =>
  value.charAt(0).toUpperCase() + value.slice(1);
function FilterGroup({
  field,
  options,
  selected,
  onToggle,
}: {
  field: FilterKey;
  options: string[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  const [search, setSearch] = useState("");
  const id = useId();
  const shown = options.filter((o) => normalize(o).includes(normalize(search)));
  return (
    <details className="filter-group" open>
      <summary>
        {labels[field]}
        {selected.length > 0 && (
          <span className="filter-count">{selected.length}</span>
        )}
        <ChevronDown size={15} />
      </summary>
      {(field === "brand" || field === "note" || field === "accord") && (
        <div className="filter-search">
          <Search size={13} />
          <input
            type="search"
            aria-label={`Search ${labels[field].toLowerCase()} filters`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Find a ${field === "brand" ? "brand" : field === "note" ? "note" : "accord"}…`}
          />
        </div>
      )}
      <div className="filter-options">
        {shown.map((option, i) => (
          <label key={option} htmlFor={`${id}-${i}`}>
            <input
              id={`${id}-${i}`}
              type="checkbox"
              checked={selected.includes(option)}
              onChange={() => onToggle(option)}
            />
            <span>{labelValue(option)}</span>
          </label>
        ))}
        {!shown.length && (
          <p className="filter-hint">
            {options.length
              ? "No matches."
              : "Available as profiles are enriched."}
          </p>
        )}
      </div>
      {(field === "note" || field === "accord") && selected.length > 1 && (
        <p className="filter-hint">
          Matches all selected {field === "note" ? "notes" : "accords"}.
        </p>
      )}
    </details>
  );
}
export function Filters({
  perfumes,
  query,
  change,
}: {
  perfumes: Perfume[];
  query: CatalogQuery;
  change: (patch: Partial<CatalogQuery>) => void;
}) {
  const toggle = (field: FilterKey, option: string) =>
    change({
      [field]: query[field].includes(option)
        ? query[field].filter((v) => v !== option)
        : [...query[field], option],
    });
  return (
    <div className="filters-inner">
      <div className="filters-heading">
        <h2>Refine your search</h2>
        <button
          className="text-button"
          onClick={() =>
            change({
              brand: [],
              gender: [],
              season: [],
              note: [],
              accord: [],
            })
          }
        >
          Reset
        </button>
      </div>
      {filterKeys.map((field) => (
        <FilterGroup
          key={field}
          field={field}
          options={[
            ...new Set([
              ...perfumes.flatMap((p) => values(p, field)),
              ...query[field],
            ]),
          ].sort((a, b) => a.localeCompare(b))}
          selected={query[field]}
          onToggle={(value) => toggle(field, value)}
        />
      ))}
    </div>
  );
}
export function FilterChips({
  query,
  change,
}: {
  query: CatalogQuery;
  change: (patch: Partial<CatalogQuery>) => void;
}) {
  return (
    <div className="filter-chips">
      {filterKeys.flatMap((key) =>
        query[key].map((value) => (
          <button
            key={`${key}-${value}`}
            onClick={() =>
              change({ [key]: query[key].filter((v) => v !== value) })
            }
            aria-label={`Remove ${value} ${labels[key]} filter`}
          >
            {labelValue(value)}
            <X size={12} />
          </button>
        )),
      )}
    </div>
  );
}
