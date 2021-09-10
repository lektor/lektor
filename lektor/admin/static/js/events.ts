export type LektorEvents = {
  "lektor-attachments-changed": string;
  "lektor-dialog": { type: "find-files" | "refresh" | "publish" };
  "lektor-error": unknown;
};

/** Dispatch one of the custom events. */
export function dispatch<T extends keyof LektorEvents>(
  type: T,
  detail: LektorEvents[T]
): void {
  document.dispatchEvent(new CustomEvent(type, { detail }));
}

/** Subscribe to one of Lektor's custom events. */
export function subscribe<T extends keyof LektorEvents>(
  type: T,
  handler: (ev: CustomEvent<LektorEvents[T]>) => void
): void {
  document.addEventListener(type, handler as EventListener);
}

/** Subscribe from one of Lektor's custom events. */
export function unsubscribe<T extends keyof LektorEvents>(
  type: T,
  handler: (ev: CustomEvent<LektorEvents[T]>) => void
): void {
  document.removeEventListener(type, handler as EventListener);
}
