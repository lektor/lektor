import { useCallback } from "react";
import { useHistory } from "react-router-dom";
import { PageName, RecordPathDetails } from "./RecordComponent";

type Path = RecordPathDetails["path"];
type Alt = RecordPathDetails["alt"];

/**
 * Compute an admin path.
 * @param page - e.g. edit or preview
 * @param path - fs path to the record
 * @param alt - the alternative to use.
 * @returns
 */
export function adminPath(page: PageName, path: Path, alt: Alt): string {
  const params = new URLSearchParams({ path });
  if (alt !== "_primary") {
    params.set("alt", alt);
  }
  return `${$LEKTOR_CONFIG.admin_root}/${page}?${params}`;
}

/**
 * Use a function to change the admin page.
 * @returns A function to navigate to an admin page for a given view
 *          and page fs path and alt.
 */
export function useGoToAdminPage() {
  const history = useHistory();

  return useCallback(
    (name: PageName, path: Path, alt: Alt) => {
      history.push(adminPath(name, path, alt));
    },
    [history]
  );
}
