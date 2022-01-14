import { useMemo } from "react";
import { useLocation } from "react-router-dom";

import { trimSlashes } from "../utils";

/** Details about the path to a Lektor record. */
export type RecordPathDetails = {
  /** Path of the current record (Lektor db path). */
  path: `/${string}`;
  /** The alternative of the record. */
  alt: string;
};

export const PAGE_NAMES = [
  "edit",
  "delete",
  "preview",
  "add-child",
  "upload",
] as const;
export type PageName = typeof PAGE_NAMES[number];

export type RecordProps = { page: PageName; record: RecordPathDetails };

// Fake useSearchParams from react-router-dom v6
// FIXME: move this
function useSearchParams() {
  const { search } = useLocation();
  const params = useMemo(() => new URLSearchParams(search), [search]);
  return [params];
}

export function useRecord(): RecordPathDetails {
  const [searchParams] = useSearchParams();

  return {
    path: `/${trimSlashes(searchParams.get("path") ?? "/")}`,
    alt: searchParams.get("alt") ?? "_primary",
  };
}
