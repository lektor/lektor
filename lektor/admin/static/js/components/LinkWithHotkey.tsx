import React, {
  MutableRefObject,
  ReactNode,
  useCallback,
  useEffect,
  useRef,
} from "react";
import { NavLink } from "react-router-dom";
import { getKey, KeyboardShortcut, keyboardShortcutHandler } from "../utils";

/**
 * React hook to add a global keyboard shortcut for the given
 * key for the lifetime of the component.
 */
function useKeyboardShortcut(
  key: KeyboardShortcut,
  action: (ev: KeyboardEvent) => void
): void {
  useEffect(() => {
    const handler = keyboardShortcutHandler(key, action);
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [key, action]);
}

/**
 * Add a global keyboard shortcut for the given key and simulate
 * a click on the ref'ed element.
 */
function useKeyboardShortcutRef<T extends HTMLElement>(
  key: KeyboardShortcut
): MutableRefObject<T | null> {
  const el = useRef<T | null>(null);
  const handler = useCallback(() => {
    el.current?.click();
  }, []);
  useKeyboardShortcut(key, handler);
  return el;
}

export default function LinkWithHotkey(props: {
  to: string;
  children: ReactNode;
  shortcut: KeyboardShortcut;
}) {
  let path = props.to;
  if (path.substr(0, 1) !== "/") {
    path = `${$LEKTOR_CONFIG.admin_root}/${path}`;
  }
  const el = useKeyboardShortcutRef<HTMLAnchorElement>(props.shortcut);

  return (
    <NavLink
      to={path}
      activeClassName="active"
      title={getKey(props.shortcut)}
      ref={el}
    >
      {props.children}
    </NavLink>
  );
}
