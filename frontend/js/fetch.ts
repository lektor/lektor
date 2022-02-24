import { RecordInfo } from "./components/types";
import {
  RecordAlternative,
  RecordPath,
  RecordPathDetails,
} from "./context/record-context";
import { SearchResult } from "./dialogs/find-files/FindFiles";
import { Server } from "./dialogs/Publish";
import { RecordPathInfoSegment } from "./header/BreadCrumbs";
import { NewRecordInfo } from "./views/add-child-page/types";
import { RawRecord } from "./views/edit/EditPage";

export class FetchError extends Error {
  constructor(readonly code: string) {
    super();
  }
}

/**
 * Handle a JSON response - throw on HTTP error.
 */
function handleJSON(response: Response) {
  if (!response.ok) {
    throw new FetchError("REQUEST_FAILED");
  }
  return response.json();
}

const credentials = "same-origin";
const headers = { "Content-Type": "application/json" };

/**
 * Helper to execute one of the fetch requests to the Lektor admin API.
 */
function fetchJSON(
  input: string,
  method: "GET" | "POST" | "PUT",
  json?: unknown
): Promise<unknown> {
  const init: RequestInit =
    json === undefined
      ? { credentials, method }
      : { credentials, method, headers, body: JSON.stringify(json) };
  return fetch(input, init).then(handleJSON);
}

/** Required URL parameters for GET API endpoints. */
type GetAPIParams = {
  "/matchurl": { url_path: string };
  "/newattachment": { path: RecordPath };
  "/newrecord": { path: RecordPath; alt?: RecordAlternative };
  "/pathinfo": { path: RecordPath };
  "/ping": null;
  "/previewinfo": RecordPathDetails;
  "/rawrecord": RecordPathDetails;
  "/recordinfo": { path: RecordPath };
  "/servers": null;
};

/** Type of the returned JSON for GET API endpoints. */
type GetAPIReturns = {
  "/matchurl": RecordPathDetails & { exists: boolean };
  "/newattachment": { label: string; can_upload: boolean };
  "/newrecord": NewRecordInfo;
  "/pathinfo": { segments: RecordPathInfoSegment[] };
  "/ping": { project_id: string };
  "/previewinfo": { url: string | null };
  "/rawrecord": RawRecord;
  "/recordinfo": RecordInfo;
  "/servers": { servers: Server[] };
};

/**
 * Required URL parameters for POST API endpoints.
 * Currently one endpoint (newrecord) has the data sent as JSON which isn't typed yet.
 */
type PostAPIParams = {
  "/browsefs": RecordPathDetails;
  "/build": null;
  "/clean": null;
  "/deleterecord": RecordPathDetails & { delete_master: "1" | "0" };
  "/find": { q: string; alt: RecordAlternative; lang: string };
  "/newrecord": null; // it's all in the JSON request.
};

/** Type of the returned JSON for POST API endpoints. `unknown` in case that it isn't used */
type PostAPIReturns = {
  "/browsefs": { okay: boolean };
  "/build": unknown;
  "/clean": unknown;
  "/deleterecord": unknown;
  "/find": { results: SearchResult[] };
  "/newrecord": { valid_id: boolean; exists: boolean; path: RecordPath };
};

/**
 * Required JSON data for PUT API endpoints.
 */
type PutAPIData = {
  "/rawrecord": RecordPathDetails & { data: Record<string, string | null> };
};

/** Type of the returned JSON for PUT API endpoints. `unknown` in case that it isn't used */
type PutAPIReturns = {
  "/rawrecord": unknown;
};

/**
 * URL to one of Lektor's API endpoints with query string.
 * @param endpoint - the API endpoint
 * @param params - possible URL parameters to include in the query string
 * @returns the absolute API URL with query string.
 */
export function apiUrl(
  endpoint: string,
  params?: Record<string, string> | null
): string {
  const url = `${$LEKTOR_CONFIG.admin_root}/api${endpoint}`;
  if (params) {
    const urlParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      urlParams.set(key, value);
    });
    return `${url}?${urlParams.toString()}`;
  }
  return url;
}

/**
 * Load data from the JSON API.
 * @param endpoint - The API endpoint to get.
 * @param params - URL params to set.
 * @param json - Possible JSON body of the request.
 */
export function get<T extends keyof GetAPIReturns>(
  endpoint: T,
  params: GetAPIParams[T]
): Promise<GetAPIReturns[T]> {
  const url = apiUrl(endpoint, params);
  return fetchJSON(url, "GET") as Promise<GetAPIReturns[T]>;
}

/**
 * Execute a POST api request.
 * @param endpoint - The API endpoint to POST to.
 * @param params - URL params to set.
 * @param json - Possible JSON body of the request.
 */
export function post<T extends keyof PostAPIReturns>(
  endpoint: T,
  params: PostAPIParams[T],
  json?: unknown
): Promise<PostAPIReturns[T]> {
  const url = apiUrl(endpoint, params);
  return fetchJSON(url, "POST", json) as Promise<PostAPIReturns[T]>;
}

/**
 * Execute a PUT api request.
 * @param endpoint - The API endpoint to PUT to.
 * @param json - Possible JSON body of the request.
 */
export function put<T extends keyof PutAPIReturns>(
  endpoint: T,
  json: PutAPIData[T]
): Promise<PutAPIReturns[T]> {
  const url = apiUrl(endpoint);
  return fetchJSON(url, "PUT", json);
}
