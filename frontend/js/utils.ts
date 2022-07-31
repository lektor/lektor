import { RecordPath } from "./context/record-context";

export function isValidUrl(url: string): boolean {
  return !!url.match(/^([a-z0-9+.-]+):(\/\/)?[^/]\S+$/);
}

/**
 * Trim leading slashes from a string.
 */
export function trimLeadingSlashes(string: string): string {
  const match = /^\/*(.*?)$/.exec(string);
  return match ? match[1] : "";
}

/**
 * Trim trailing slashes from a string.
 */
export function trimTrailingSlashes(string: string): string {
  const match = /^(.*?)\/*$/.exec(string);
  return match ? match[1] : "";
}

/**
 * Trim both leading and trailing slashes from a string.
 */
export function trimSlashes(string: string): string {
  const match = /^\/*(.*?)\/*$/.exec(string);
  return match ? match[1] : "";
}

/**
 * Trim both leading and trailing colons from a string.
 */
export function trimColons(string: string): string {
  const match = /^:*(.*?):*$/.exec(string);
  return match ? match[1] : "";
}

export function getCanonicalUrl(localPath: string): string {
  const base = trimTrailingSlashes($LEKTOR_CONFIG.site_root);
  return `${base}/${trimLeadingSlashes(localPath)}`;
}

export function getPlatform(): "windows" | "mac" | "linux" | null {
  try {
    const appVersion = navigator?.appVersion;
    if (appVersion?.match(/Win/)) {
      return "windows";
    } else if (appVersion?.match(/\bMac/)) {
      return "mac";
    } else if (appVersion?.match(/\b(X11|Linux)/)) {
      return "linux";
    }
    return null;
  } catch (e) {
    return null;
  }
}

export function getParentPath(path: RecordPath): RecordPath | null {
  const match = /^(\/.*)\/[^/]*$/.exec(path);
  return match ? (match[1] as RecordPath) : null;
}
