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

export function getPlatform(): "windows" | "mac" | "linux" | "other" {
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

export interface KeyboardShortcut {
  key: string;
  mac?: string;
  preventDefault?: boolean;
}

export function getKey(shortcut: KeyboardShortcut): string {
  return getPlatform() === "mac" && shortcut.mac ? shortcut.mac : shortcut.key;
}

export function keyboardShortcutHandler(
  shortcut: KeyboardShortcut,
  action: (ev: KeyboardEvent) => void
): (ev: KeyboardEvent) => void {
  const key = getKey(shortcut);
  return (ev) => {
    let eventKey = ev.key;
    if (ev.altKey) {
      eventKey = `Alt+${eventKey}`;
    }
    if (ev.ctrlKey) {
      eventKey = `Control+${eventKey}`;
    }
    if (ev.metaKey) {
      eventKey = `Meta+${eventKey}`;
    }
    if (eventKey === key) {
      if (shortcut.preventDefault) {
        ev.preventDefault();
      }
      action(ev);
    }
  };
}

export function getParentPath(path: RecordPath): RecordPath | null {
  const match = /^(\/.*)\/[^/]*$/.exec(path);
  return match ? (match[1] as RecordPath) : null;
}
