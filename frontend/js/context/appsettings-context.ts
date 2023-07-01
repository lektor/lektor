import { createContext, useContext } from "react";
import {
  defaultShortcutKeyMap,
  serializeShortcutKeyMap,
  deserializeShortcutKeyMap,
  ShortcutKeyMap,
} from "../shortcut-keys";

export interface AppSettings {
  shortcutKeyMap: ShortcutKeyMap;
}

export const defaultAppSettings: AppSettings = {
  shortcutKeyMap: defaultShortcutKeyMap,
} as const;

export const AppSettingsContext =
  createContext<AppSettings>(defaultAppSettings);

export function useAppSettings(): AppSettings {
  return useContext(AppSettingsContext);
}

function serializeAppSettings(settings: AppSettings) {
  return {
    shortcutKeyMap: serializeShortcutKeyMap(settings.shortcutKeyMap),
  };
}

function hasAttribute<Obj, Attr extends string>(
  obj: Obj,
  attr: Attr,
): obj is Obj & Record<Attr, unknown> {
  return typeof obj === "object" && obj !== null && attr in obj;
}

function deserializeAppSettings(obj: unknown): AppSettings {
  if (!hasAttribute(obj, "shortcutKeyMap")) {
    throw new Error("Bad stored value for AppSettings");
  }
  return {
    shortcutKeyMap: deserializeShortcutKeyMap(obj.shortcutKeyMap),
  };
}

const appSettingsKey = "com.getlektor--appsettings";

export function loadAppSettings(): AppSettings {
  try {
    const saved = localStorage.getItem(appSettingsKey);
    if (saved) {
      return deserializeAppSettings(JSON.parse(saved));
    }
  } catch (e) {
    console.log("Failed to load AppSettings from localStorage", e);
  }
  return defaultAppSettings;
}

export function saveAppSettings(settings: AppSettings): void {
  localStorage.setItem(
    appSettingsKey,
    JSON.stringify(serializeAppSettings(settings)),
  );
}
