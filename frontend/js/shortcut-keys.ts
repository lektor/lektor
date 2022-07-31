import React, { ModifierKey } from "react";
import { getPlatform } from "./utils";

export enum ShortcutAction {
  Edit = "EDIT_SHORTCUT",
  Save = "SAVE_SHORTCUT",
  Preview = "PREVIEW_SHORTCUT", // NB: saves any pending changes in edit view
  Search = "SEARCH_SHORTCUT",
}

type OptMeta = "Meta+" | "";
type OptCtrl = "Control+" | "";
type OptAlt = "Alt+" | "";
type OptShift = "Shift+" | "";
type Modifier = Exclude<`${OptMeta}${OptCtrl}${OptAlt}${OptShift}`, "">;

export type ShortcutKey = `${Modifier}${Capitalize<KeyboardEvent["key"]>}`;

const shortcutKeyRegexp = new RegExp(
  [
    "^",
    "(?:Meta\\+)?(?:Control\\+)?(?:Alt\\+)?(?:Shift\\+)?",
    "(?<=\\+)[A-Z]\\w*",
    "$",
  ].join("")
);

function isValidShortcutKey(value: unknown): value is ShortcutKey {
  return typeof value === "string" && shortcutKeyRegexp.test(value);
}

export type ShortcutKeyMap = Map<ShortcutAction, ShortcutKey | null>;

function mod(key: Capitalize<string>): ShortcutKey {
  const defaultMod = getPlatform() === "mac" ? "Meta" : "Control";
  return `${defaultMod}+${key}`;
}

export const defaultShortcutKeyMap: ShortcutKeyMap = new Map([
  [ShortcutAction.Edit, mod("E")],
  [ShortcutAction.Preview, mod("S")],
  [ShortcutAction.Save, null],
  [ShortcutAction.Search, mod("G")],
]);

export function getShortcutKey(
  event: KeyboardEvent | React.KeyboardEvent
): ShortcutKey | null {
  const mods: Array<ModifierKey> = ["Meta", "Control", "Alt", "Shift"];
  if (!mods.every((mod) => event.key !== mod)) {
    return null;
  }
  const activeMods = mods.filter((mod) => event.getModifierState(mod));
  if (activeMods.length === 0) {
    return null;
  }
  const key = event.key.length == 1 ? event.key.toUpperCase() : event.key;
  return [...activeMods, key].join("+") as ShortcutKey;
}

const shortcutHandlers = new Map<ShortcutAction, () => void>();

export function setShortcutHandler(
  action: ShortcutAction,
  handler: () => void
): () => void {
  const prevHandler = shortcutHandlers.get(action);
  shortcutHandlers.set(action, handler);

  return () =>
    prevHandler
      ? shortcutHandlers.set(action, prevHandler)
      : shortcutHandlers.delete(action);
}

function dispatchShortcut(action: ShortcutAction): void {
  const handler = shortcutHandlers.get(action);
  if (handler) {
    handler();
  }
}

export function installShortcutKeyListener(keymap: ShortcutKeyMap) {
  const actionForKey = new Map(
    Array.from(keymap.entries())
      .filter(([, key]) => key)
      .map(([action, key]) => [key, action])
  );

  const keydownListener = (event: KeyboardEvent) => {
    const key = getShortcutKey(event);
    const action = key && actionForKey.get(key);
    if (action) {
      event.preventDefault();
      event.stopPropagation();
      dispatchShortcut(action);
    }
  };
  window.addEventListener("keydown", keydownListener);
  return () => window.removeEventListener("keydown", keydownListener);
}

export function serializeShortcutKeyMap(keymap: ShortcutKeyMap) {
  return Object.fromEntries(
    Array.from(keymap.entries()).filter(([, key]) => key)
  );
}

export function deserializeShortcutKeyMap(obj: unknown): ShortcutKeyMap {
  const data = obj as Record<string, unknown>;
  return new Map(
    Array.from(defaultShortcutKeyMap.keys(), (action) => {
      const key = data[action] ?? null;
      if (key !== null && !isValidShortcutKey(key)) {
        throw new Error("Invalid value for ShortcutKey in serialized keymap");
      }
      return [action, key];
    })
  );
}
