import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { PageName } from "../context/page-context";
import { RecordAlternative, RecordPath } from "../context/record-context";

/**
 * Compute an admin path.
 * @param page - e.g. edit or preview
 * @param path - fs path to the record
 * @param alt - the alternative to use.
 * @returns
 */
export function adminPath(
  page: PageName,
  path: RecordPath,
  alt: RecordAlternative
): string {
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
  const navigate = useNavigate();

  return useCallback(
    (name: PageName, path: RecordPath, alt: RecordAlternative) => {
      navigate(adminPath(name, path, alt));
    },
    [navigate]
  );
}
