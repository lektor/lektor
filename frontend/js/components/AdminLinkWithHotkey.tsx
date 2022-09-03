import React, { MutableRefObject, useCallback, useEffect, useRef } from "react";
import { NavLink } from "react-router-dom";
import { useRecord } from "../context/record-context";
import { KeyboardShortcut, keyboardShortcutHandler } from "../utils";
import { AdminLinkProps } from "./AdminLink";
import { adminPath } from "./use-go-to-admin-page";

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

export default function AdminLinkWithHotkey({
  page,
  path,
  alt,
  children,
  shortcut,
  ...otherProps
}: AdminLinkProps & {
  shortcut: KeyboardShortcut;
}): JSX.Element {
  // Because we need to pass the ref in, this component is not using
  // the AdminLink component but rather duplicates it mostly.
  // This is a separate component because we want to avoid all the hooks
  // for plain links.
  const el = useKeyboardShortcutRef<HTMLAnchorElement>(shortcut);

  const current = useRecord();
  const recordMatches = path === current.path && alt === current.alt;

  return (
    <NavLink
      to={adminPath(page, path, alt)}
      className={({ isActive }) =>
        isActive && recordMatches ? "active" : undefined
      }
      ref={el}
      {...otherProps}
    >
      {children}
    </NavLink>
  );
}
