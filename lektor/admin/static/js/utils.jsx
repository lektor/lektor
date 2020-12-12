export function isValidUrl(url) {
  return !!url.match(/^(https?|ftps?):\/\/\S+$|^mailto:\S+$/);
}

function stripLeadingSlash(string) {
  return string.match(/^\/*(.*?)$/)[1];
}

function stripTrailingSlash(string) {
  return string.match(/^(.*?)\/*$/)[1];
}

function addToSet(originalSet, value) {
  for (let i = 0; i < originalSet.length; i++) {
    if (originalSet[i] === value) {
      return originalSet;
    }
  }
  const rv = originalSet.slice();
  rv.push(value);
  return rv;
}

function removeFromSet(originalSet, value) {
  let rv = null;
  let off = 0;
  for (let i = 0; i < originalSet.length; i++) {
    if (originalSet[i] === value) {
      if (rv === null) {
        rv = originalSet.slice();
      }
      rv.splice(i - off++, 1);
    }
  }
  return rv === null ? originalSet : rv;
}
export function getCanonicalUrl(localPath) {
  return (
    $LEKTOR_CONFIG.site_root.match(/^(.*?)\/*$/)[1] +
    "/" +
    stripLeadingSlash(localPath)
  );
}

export function flipSetValue(originalSet, value, isActive) {
  if (isActive) {
    return addToSet(originalSet || [], value);
  } else {
    return removeFromSet(originalSet || [], value);
  }
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

function handleJSON(response) {
  if (!response.ok) {
    throw new Error({
      code: "REQUEST_FAILED",
    });
  }
  return response.json();
}

function paramsToQueryString(params) {
  const urlParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    urlParams.set(key, value);
  });
  return urlParams.toString();
}

/**
 * Load data from the JSON API.
 * @param {string} url - The API endpoint to fetch
 * @param {Record<string,string> | null} params - URL params to set.
 * @param {any} options - Additional fetch options, like the HTTP method.
 *                        If this contains a `json` key, that will be encoded to JSON
 *                        and sent as a request with the appropriate content type.
 */
export function loadData(url, params, options) {
  const apiUrl = `${$LEKTOR_CONFIG.admin_root}/api${url}`;
  const fetchUrl = params ? `${apiUrl}?${paramsToQueryString(params)}` : apiUrl;

  if (options && options.json !== undefined) {
    options.body = JSON.stringify(options.json);
    options.headers = { "Content-Type": "application/json" };
    delete options.json;
  }

  return fetch(fetchUrl, {
    credentials: "same-origin",
    method: "GET",
    ...options,
  }).then(handleJSON);
}
