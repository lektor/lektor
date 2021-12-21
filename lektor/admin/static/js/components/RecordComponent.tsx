import { useMemo } from "react";
import { useLocation } from "react-router-dom";

/** Details about the path to a Lektor record. */
export type RecordPathDetails = {
  /** Path of the current record (filesystem path). */
  path: string;
  /** The alternative of the record. */
  alt: string;
};

export type RecordProps = { page: string; record: RecordPathDetails };

// Fake useSearchParams from react-router-dom v6
function useSearchParams() {
  const { search } = useLocation();
  const params = useMemo(() => new URLSearchParams(search), [search]);
  return [params];
}

export function useRecordAlt() {
  const [searchParams] = useSearchParams();
  return searchParams.get("alt") ?? "_primary";
}
