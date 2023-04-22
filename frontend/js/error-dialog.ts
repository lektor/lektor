import { dispatch } from "./events";
import { FetchError } from "./fetch";

export function showErrorDialog(error: unknown): never {
  if (error instanceof FetchError) {
    dispatch("lektor-error", error);
  } else {
    console.error("unknown error:", error);
  }
  throw error;
}
