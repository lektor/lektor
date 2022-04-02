import { useEffect } from "react";

export type LektorEvents = {
  "lektor-attachments-changed": string;
  "lektor-dialog": { type: "find-files" | "refresh" | "publish" };
  "lektor-error": { code: string };
  "lektor-notification": { message: string };
};

/** Dispatch one of the custom events. */
export function dispatch<T extends keyof LektorEvents>(
  type: T,
  detail: LektorEvents[T]
): void {
  document.dispatchEvent(new CustomEvent(type, { detail }));
}

/** Subscribe to one of Lektor's custom events. */
function subscribe<T extends keyof LektorEvents>(
  type: T,
  handler: (ev: CustomEvent<LektorEvents[T]>) => void
): void {
  document.addEventListener(type, handler as EventListener);
}

/** Subscribe from one of Lektor's custom events. */
function unsubscribe<T extends keyof LektorEvents>(
  type: T,
  handler: (ev: CustomEvent<LektorEvents[T]>) => void
): void {
  document.removeEventListener(type, handler as EventListener);
}

/**
 * Use a subscription to one of the Lektor's events.
 *
 * The handler should be wrapped in a use callback to avoid frequent
 * re-attaching of the event handler.
 */
export function useLektorEvent<T extends keyof LektorEvents>(
  type: T,
  handler: (ev: CustomEvent<LektorEvents[T]>) => void
) {
  useEffect(() => {
    subscribe(type, handler);
    return () => unsubscribe(type, handler);
  }, [type, handler]);
}
