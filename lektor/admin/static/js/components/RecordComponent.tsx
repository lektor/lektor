import { useHistory } from "react-router";
import { urlToFsPath, fsToUrlPath } from "../utils";

export function getRecordPathAndAlt(
  path: string
): [string | null, string | null] {
  if (!path) {
    return [null, null];
  }
  const [p, a] = path.split(/\+/, 2);
  return [urlToFsPath(p), a];
}

/**
 * Helper to generate URL path for an admin page.
 * @param name - Name of the page (or null for the current one)
 * @param path - Record path
 */
export function pathToAdminPage(name: string, path: string) {
  return `${$LEKTOR_CONFIG.admin_root}/${path}/${name}`;
}

/** Details about the path to a Lektor record. */
interface RecordPathDetails {
  /** Path of the current record (or null). */
  path: string | null;
  /** The alternative of the record (or '_primary'). */
  alt: string;
}

/**
 * Extract a file system path and the alt from an URL path.
 * @param urlPath - A url path, i.e., a path with `:` as a separator and
 *                  potentially an alt appended with `+` at the end.
 */
export function getRecordDetails(urlPath: string): RecordPathDetails {
  const [path, alt] = getRecordPathAndAlt(urlPath);
  return {
    path,
    alt: !alt ? "_primary" : alt,
  };
}

export type RecordProps = {
  match: { params: { path: string; page: string } };
  record: RecordPathDetails;
  history: ReturnType<typeof useHistory>;
};

/**
 * Get the URL record path for a given record fs path.
 * @param path
 * @param alt
 */
export function getUrlRecordPathWithAlt(
  path: string | null,
  alt: string
): string {
  const urlPath = fsToUrlPath(path || "");
  return alt === "_primary" ? urlPath : `${urlPath}+${alt}`;
}
