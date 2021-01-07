class FetchError extends Error {
  constructor(readonly code: string) {
    super();
  }
}

function handleJSON(response: Response) {
  if (!response.ok) {
    throw new FetchError("REQUEST_FAILED");
  }
  return response.json();
}

function paramsToQueryString(params: Record<string, string | null>) {
  const urlParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null) {
      urlParams.set(key, value);
    }
  });
  return urlParams.toString();
}

/**
 * Load data from the JSON API.
 * @param url - The API endpoint to fetch
 * @param  params - URL params to set.
 * @param options - Additional fetch options, like the HTTP method.
 *                  If this contains a `json` key, that will be encoded to JSON
 *                  and sent as a request with the appropriate content type.
 */

export function loadData(
  url: string,
  params: Record<string, string | null> | null,
  options?: any
) {
  const apiUrl = `${$LEKTOR_CONFIG.admin_root}/api${url}`;
  const fetchUrl = params ? `${apiUrl}?${paramsToQueryString(params)}` : apiUrl;

  if (options && options.json !== undefined) {
    options.body = JSON.stringify(options.json);
    options.headers = { "Content-Type": "application/json" };
    delete options.json;
  }

  return fetch(fetchUrl, {
    credentials: "same-origin",
    method: "GET",
    ...options,
  }).then(handleJSON);
}
