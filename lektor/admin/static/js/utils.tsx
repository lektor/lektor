export function isValidUrl(url: string) {
  return !!url.match(/^(https?|ftps?):\/\/\S+$|^(mailto|webcal|feed):\S+$/);
}

/**
 * Trim leading slashes from a string.
 */
export function stripLeadingSlashes(string: string) {
  const match = /^\/*(.*?)$/.exec(string);
  return match ? match[1] : "";
}

/**
 * Trim trailing slashes from a string.
 */
export function stripTrailingSlashes(string: string) {
  const match = /^(.*?)\/*$/.exec(string);
  return match ? match[1] : "";
}

/**
 * Trim both leading and trailing slashes from a string.
 */
export function trimSlashes(string: string) {
  const match = /^\/*(.*?)\/*$/.exec(string);
  return match ? match[1] : "";
}

/**
 * Trim both leading and trailing colons from a string.
 */
export function trimColons(string: string) {
  const match = /^:*(.*?):*$/.exec(string);
  return match ? match[1] : "";
}

export function getCanonicalUrl(localPath: string) {
  const base = stripTrailingSlashes($LEKTOR_CONFIG.site_root);
  return `${base}/${stripLeadingSlashes(localPath)}`;
}

export function urlPathsConsideredEqual(a: string | null, b: string | null) {
  if (a == null || b == null) {
    return false;
  }
  return stripTrailingSlashes(a) === stripTrailingSlashes(b);
}

export function getApiUrl(url: string) {
  return `${$LEKTOR_CONFIG.admin_root}/api${url}`;
}

export function getPlatform() {
  if (navigator.appVersion.indexOf("Win") !== -1) {
    return "windows";
  } else if (navigator.appVersion.indexOf("Mac") !== -1) {
    return "mac";
  } else if (
    navigator.appVersion.indexOf("X11") !== -1 ||
    navigator.appVersion.indexOf("Linux") !== -1
  ) {
    return "linux";
  }
  return "other";
}

/**
 * Whether the meta key (command on Mac, Ctrl otherwise) and no other control
 * keys is pressed.
 * @param event - A keyboard event.
 */
export function isMetaKey(event: KeyboardEvent) {
  return getPlatform() === "mac"
    ? event.metaKey && !event.altKey && !event.shiftKey
    : event.ctrlKey && !event.altKey && !event.shiftKey;
}

export function getParentFsPath(fsPath: string) {
  const match = /^(.*?)\/([^/]*)$/.exec(fsPath);
  return match ? match[1] : null;
}

export function fsToUrlPath(fsPath: string) {
  let segments = trimSlashes(fsPath).split("/");
  if (segments.length === 1 && segments[0] === "") {
    segments = [];
  }
  segments.unshift("root");
  return segments.join(":");
}

export function urlToFsPath(urlPath: string) {
  const segments = trimColons(urlPath).split(":");
  if (segments.length < 1 || segments[0] !== "root") {
    return null;
  }
  segments[0] = "";
  return segments.join("/");
}

export function fsPathFromAdminObservedPath(adminPath: string) {
  const base = stripTrailingSlashes($LEKTOR_CONFIG.site_root);
  if (adminPath.substr(0, base.length) !== base) {
    return null;
  }
  return "/" + trimSlashes(adminPath.substr(base.length));
}
