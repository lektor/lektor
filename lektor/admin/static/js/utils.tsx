export function isValidUrl(url: string) {
  return !!url.match(/^(https?|ftps?):\/\/\S+$|^mailto:\S+$/);
}

export function stripLeadingSlash(string: string) {
  const match = /^\/*(.*?)$/.exec(string);
  return match ? match[1] : "";
}

export function stripTrailingSlash(string: string) {
  const match = /^(.*?)\/*$/.exec(string);
  return match ? match[1] : "";
}

export function getCanonicalUrl(localPath: string) {
  return (
    $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1] +
    "/" +
    stripLeadingSlash(localPath)
  );
}

export function urlPathsConsideredEqual(a: string | null, b: string | null) {
  if (a == null || b == null) {
    return false;
  }
  return stripTrailingSlash(a) === stripTrailingSlash(b);
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
  return fsPath.match(/^(.*?)\/([^/]*)$/)[1];
}

export function fsToUrlPath(fsPath: string) {
  let segments = fsPath.match(/^\/*(.*?)\/*$/)[1].split("/");
  if (segments.length === 1 && segments[0] === "") {
    segments = [];
  }
  segments.unshift("root");
  return segments.join(":");
}

export function urlToFsPath(urlPath: string) {
  const segments = urlPath.match(/^:*(.*?):*$/)[1].split(":");
  if (segments.length < 1 || segments[0] !== "root") {
    return null;
  }
  segments[0] = "";
  return segments.join("/");
}

export function fsPathFromAdminObservedPath(adminPath: string) {
  const base = $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1];
  if (adminPath.substr(0, base.length) !== base) {
    return null;
  }
  return "/" + adminPath.substr(base.length).match(/^\/*(.*?)\/*$/)[1];
}
