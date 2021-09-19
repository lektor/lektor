import { dispatch } from "./events";

export function showErrorDialog(error: unknown): void {
  dispatch("lektor-error", error);
}
