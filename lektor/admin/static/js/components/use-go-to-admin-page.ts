import { useCallback } from "react";
import { useHistory } from "react-router-dom";
import { fsToUrlPath } from "../utils";

/**
 * Compute an admin path.
 * @param page - e.g. edit or preview
 * @param path - fs path to the record
 * @param alt - the alternative to use.
 * @returns
 */
export function adminPath(page: string, path: string, alt: string): string {
  const urlPath = fsToUrlPath(path);
  const urlPathWithAlt = alt === "_primary" ? urlPath : `${urlPath}+${alt}`;
  return `${$LEKTOR_CONFIG.admin_root}/${urlPathWithAlt}/${page}`;
}

/**
 * Use a function to change the admin page.
 * @returns A function to navigate to an admin page for a given view
 *          and page fs path and alt.
 */
export function useGoToAdminPage() {
  const history = useHistory();

  return useCallback(
    (name: string, path: string, alt: string) => {
      history.push(adminPath(name, path, alt));
    },
    [history]
  );
}
