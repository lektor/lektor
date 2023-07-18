import { createContext, useContext } from "react";

/** Path to a Lektor record. */
export type RecordPath = `/${string}`;
/** Alternative of a Lektor record. */
export type RecordAlternative = string;

/** Details about the path to a Lektor record. */
export type RecordPathDetails = {
  /** Path of the current record (Lektor db path). */
  path: RecordPath;
  /** The alternative of the record. */
  alt: RecordAlternative;
};

export const RecordContext = createContext<RecordPathDetails>({
  path: "/",
  alt: "_primary",
});

/** The current record. */
export function useRecord(): RecordPathDetails {
  return useContext(RecordContext);
}

/** The alternative of the currently active record. */
export function useRecordAlt(): string {
  const record = useRecord();
  return record.alt;
}

/** The path of the currently active record. */
export function useRecordPath(): RecordPath {
  const record = useRecord();
  return record.path;
}
