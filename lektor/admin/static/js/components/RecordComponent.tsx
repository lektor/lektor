import { urlToFsPath } from "../utils";

/** Details about the path to a Lektor record. */
export type RecordPathDetails = {
  /** Path of the current record (filesystem path). */
  path: string;
  /** The alternative of the record. */
  alt: string;
};

/**
 * Extract a file system path and the alt from an URL path.
 * @param urlPath - A url path, i.e., a path with `:` as a separator and
 *                  potentially an alt appended with `+` at the end.
 */
export function getRecordDetails(urlPath: string): RecordPathDetails | null {
  if (!urlPath) {
    return null;
  }
  const [p, a] = urlPath.split(/\+/, 2);
  const [path, alt] = [urlToFsPath(p), a];
  return path !== null ? { path, alt: alt || "_primary" } : null;
}

export type RecordProps = { page: string; record: RecordPathDetails };
