import { dispatch } from "./events";

export function showErrorDialog(error: unknown) {
  dispatch("lektor-error", error);
}
