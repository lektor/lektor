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
 * @param name - Name of the page (or null for the current one).
 * @param path - Record (URL) path.
 */
export function pathToAdminPage(name: string, path: string) {
  return `${$LEKTOR_CONFIG.admin_root}/${path}/${name}`;
}

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
export function getRecordDetails(urlPath: string): {
  path: string | null;
  alt: string;
} {
  const [path, alt] = getRecordPathAndAlt(urlPath);
  return {
    path,
    alt: !alt ? "_primary" : alt,
  };
}

export type RecordProps = {
  page: string;
  record: RecordPathDetails;
  history: ReturnType<typeof useHistory>;
};

/**
 * Get the URL record path for a given record fs path.
 * @param path
 * @param alt
 */
export function getUrlRecordPath(path: string, alt: string): string {
  const urlPath = fsToUrlPath(path);
  return alt === "_primary" ? urlPath : `${urlPath}+${alt}`;
}
