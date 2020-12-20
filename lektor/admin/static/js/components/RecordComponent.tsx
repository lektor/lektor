import React from "react";
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

export type RecordProps = {
  match: { params: { path: string; page: string } };
  history: ReturnType<typeof useHistory>;
};

/**
 * A React component baseclass that has some basic knowledge about
 * the record it works with.
 */
export default class RecordComponent<
  Props extends RecordProps,
  State
> extends React.Component<Props, State> {
  /**
   * Helper to transition to a specific page
   * @param name - Page name
   * @param path - Record path
   */
  transitionToAdminPage(name: string, path: string) {
    this.props.history.push(pathToAdminPage(name, path));
  }

  /* this returns the path of the current record.  If the current page does
   * not have a path component then null is returned. */
  getRecordPath() {
    const [path] = getRecordPathAndAlt(this.props.match.params.path);
    return path;
  }

  /* returns the current alt */
  getRecordAlt() {
    const [, alt] = getRecordPathAndAlt(this.props.match.params.path);
    return !alt ? "_primary" : alt;
  }

  /* return the url path for the current record path (or a modified one)
     by preserving or overriding the alt */
  getUrlRecordPathWithAlt(newPath?: string, newAlt?: string) {
    const path = newPath ?? this.getRecordPath();
    const alt = newAlt ?? this.getRecordAlt();
    const urlPath = fsToUrlPath(path);
    return alt === "_primary" ? urlPath : `${urlPath}+${alt}`;
  }
}
