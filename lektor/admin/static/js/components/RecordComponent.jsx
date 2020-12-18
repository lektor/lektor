import React from "react";
import { getParentFsPath, urlToFsPath, fsToUrlPath } from "../utils";

export function getRecordPathAndAlt(path) {
  if (!path) {
    return [null, null];
  }
  const items = path.split(/\+/, 2);
  return [urlToFsPath(items[0]), items[1]];
}

/**
 * A React component baseclass that has some basic knowledge about
 * the record it works with.
 */
export default class RecordComponent extends React.Component {
  /**
   * Helper to generate URL path for an admin page.
   * @param {string | null} name - Name of the page (or null for the current one)
   * @param {string} path - Record path
   */
  getPathToAdminPage(name, path) {
    const pageName = name !== null ? name : this.props.match.params.page;
    return `${$LEKTOR_CONFIG.admin_root}/${path}/${pageName}`;
  }

  /**
   * Helper to transition to a specific page
   * @param {string} name - Page name
   * @param {string} path - Record path
   */
  transitionToAdminPage(name, path) {
    const url = this.getPathToAdminPage(name, path);
    this.props.history.push(url);
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
  getUrlRecordPathWithAlt(newPath, newAlt) {
    if (newPath === undefined || newPath === null) {
      newPath = this.getRecordPath();
    }
    if (newAlt === undefined || newAlt === null) {
      newAlt = this.getRecordAlt();
    }
    let rv = fsToUrlPath(newPath);
    if (newAlt !== "_primary") {
      rv += "+" + newAlt;
    }
    return rv;
  }

  /* returns the parent path if available */
  getParentRecordPath() {
    return getParentFsPath(this.getRecordPath());
  }
}
