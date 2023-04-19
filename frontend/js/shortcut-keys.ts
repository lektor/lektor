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

// These keys are never treated as shortcut keys
//
// For a possibly complete list of named keys, see
// https://www.w3.org/TR/uievents-key/#named-key-attribute-values
//
const ignoredKeys = new Set([
  "Unidentified",
  // Modifier Keys
  "Alt",
  "AltGraph",
  "CapsLock",
  "Control",
  "Fn",
  "FnLock",
  "Meta",
  "NumLock",
  "ScrollLock",
  "Shift",
  "Symbol",
  "SymbolLock",
  "Hyper",
  "Super",
  // Legacy Modifier Keys
  "Hyper",
  "Super",
]);

// These are keys that are used in the preferences dialog
// to erase the currently set hotkey.
export const eraseHotkeyKeys = new Set([
  "Backspace",
  "Delete",
  " ", // space key
]);

function isPrintingKey(key: string) {
  return key.length === 1 || key == "Enter" || key == "Tab";
}

const modifierKeys: Array<ModifierKey> = ["Meta", "Control", "Alt", "Shift"];

export function getShortcutKey(
  event: KeyboardEvent | React.KeyboardEvent
): ShortcutKey | null {
  const nativeEvent = event instanceof Event ? event : event.nativeEvent;
  if (nativeEvent.isComposing || ignoredKeys.has(event.key)) {
    return null;
  }
  const activeMods = modifierKeys.filter((mod) => event.getModifierState(mod));
  if (activeMods.length === 0 && eraseHotkeyKeys.has(event.key)) {
    return null;
  }
  if (isPrintingKey(event.key)) {
    const haveNonShiftMod = activeMods.some((mod) => mod != "Shift");
    if (!haveNonShiftMod) {
      // Printing keys are not accepted as a shortcut key
      // unless combined with a modifier (other than Shift).
      return null;
    }
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
