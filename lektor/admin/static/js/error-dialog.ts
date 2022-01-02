import { dispatch } from "./events";
import { FetchError } from "./fetch";

export function showErrorDialog(error: unknown): void {
  if (error instanceof FetchError) {
    dispatch("lektor-error", error);
  } else {
    console.error("unknown error:", error);
  }
}
