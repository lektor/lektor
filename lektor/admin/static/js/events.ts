import { Dialog } from "./dialogSystem";

type LektorEvents = {
  "lektor-attachments-changed": string;
  "lektor-dialog-changed": { dialog: Dialog | null; dialogOptions?: unknown };
};

export function dispatch<T extends keyof LektorEvents>(
  type: T,
  detail: LektorEvents[T]
): void {
  document.dispatchEvent(new CustomEvent(type, { detail }));
}

export function subscribe<T extends keyof LektorEvents>(
  type: T,
  handler: (ev: CustomEvent<LektorEvents[T]>) => void
): void {
  document.addEventListener(type, handler as EventListener);
}

export function unsubscribe<T extends keyof LektorEvents>(
  type: T,
  handler: (ev: CustomEvent<LektorEvents[T]>) => void
): void {
  document.removeEventListener(type, handler as EventListener);
}
