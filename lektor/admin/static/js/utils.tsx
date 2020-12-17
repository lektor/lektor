export function isValidUrl(url) {
  return !!url.match(/^(https?|ftps?):\/\/\S+$|^mailto:\S+$/);
}

function stripLeadingSlash(string) {
  return string.match(/^\/*(.*?)$/)[1];
}

function stripTrailingSlash(string) {
  return string.match(/^(.*?)\/*$/)[1];
}

export function getCanonicalUrl(localPath) {
  return (
    $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1] +
    "/" +
    stripLeadingSlash(localPath)
  );
}

export function urlPathsConsideredEqual(a, b) {
  if (a == null || b == null) {
    return false;
  }
  return stripTrailingSlash(a) === stripTrailingSlash(b);
}

export function getApiUrl(url) {
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
 * @param {KeyboardEvent} event - A keyboard event.
 */
export function isMetaKey(event) {
  return getPlatform() === "mac"
    ? event.metaKey && !event.altKey && !event.shiftKey
    : event.ctrlKey && !event.altKey && !event.shiftKey;
}

export function getParentFsPath(fsPath) {
  return fsPath.match(/^(.*?)\/([^/]*)$/)[1];
}

export function fsToUrlPath(fsPath) {
  let segments = fsPath.match(/^\/*(.*?)\/*$/)[1].split("/");
  if (segments.length === 1 && segments[0] === "") {
    segments = [];
  }
  segments.unshift("root");
  return segments.join(":");
}

export function urlToFsPath(urlPath) {
  const segments = urlPath.match(/^:*(.*?):*$/)[1].split(":");
  if (segments.length < 1 || segments[0] !== "root") {
    return null;
  }
  segments[0] = "";
  return segments.join("/");
}

export function fsPathFromAdminObservedPath(adminPath) {
  const base = $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1];
  if (adminPath.substr(0, base.length) !== base) {
    return null;
  }
  return "/" + adminPath.substr(base.length).match(/^\/*(.*?)\/*$/)[1];
}
