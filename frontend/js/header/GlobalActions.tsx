import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useRecord } from "../context/record-context";
import { getCanonicalUrl } from "../utils";
import { get } from "../fetch";
import { trans } from "../i18n";
import { showErrorDialog } from "../error-dialog";
import { dispatch } from "../events";
import { setShortcutHandler, ShortcutAction } from "../shortcut-keys";

const findFiles = () => {
  dispatch("lektor-dialog", { type: "find-files" });
};
const refresh = () => {
  dispatch("lektor-dialog", { type: "refresh" });
};
const publish = () => {
  dispatch("lektor-dialog", { type: "publish" });
};
const preferences = () => {
  dispatch("lektor-dialog", { type: "preferences" });
};

export default function GlobalActions(): React.JSX.Element {
  const record = useRecord();

  // Fetch previewURL so that we can use a link instead of button
  // with onclick handler for the preview button.
  // This allows one to, e.g., open a preview in a new window by
  // right-clicking on the button.
  const [previewUrl, setPreviewUrl] = useState<string | undefined>();
  const fetchPreviewUrl = useMemo(
    () =>
      get("/previewinfo", record)
        .then((response) => response.url)
        .then((url) => getCanonicalUrl(url ?? "/"))
        .then((canonicalUrl) => {
          setPreviewUrl(canonicalUrl);
          return canonicalUrl;
        })
        .catch(showErrorDialog),
    [record],
  );

  useEffect(() => {
    return setShortcutHandler(ShortcutAction.Search, findFiles);
  }, []);

  const returnToWebsite = useCallback(() => {
    if (previewUrl === null) {
      // href has not yet been set on the link button
      // wait for /previewinfo fetch to complete...
      fetchPreviewUrl
        .then((href) => {
          window.location.href = href;
        })
        .catch(showErrorDialog);
    }
  }, [previewUrl, fetchPreviewUrl]);

  return (
    <div className="btn-group">
      <button
        type="button"
        className="btn btn-secondary border"
        onClick={findFiles}
        title={trans("FIND_FILES")}
      >
        <i className="fa fa-search fa-fw" />
      </button>
      <button
        type="button"
        className="btn btn-secondary border"
        onClick={publish}
        title={trans("PUBLISH")}
      >
        <i className="fa fa-cloud-upload fa-fw" />
      </button>
      <button
        type="button"
        className="btn btn-secondary border"
        onClick={refresh}
        title={trans("REFRESH_BUILD")}
      >
        <i className="fa fa-refresh fa-fw" />
      </button>
      <a
        href={previewUrl}
        className="btn btn-secondary border"
        title={trans("RETURN_TO_WEBSITE")}
        onClick={returnToWebsite}
      >
        <i className="fa fa-eye fa-fw" />
      </a>
      <button
        type="button"
        className="btn btn-secondary border"
        onClick={preferences}
        title={trans("PREFERENCES")}
      >
        <i className="fa fa-gear fa-fw" />
      </button>
    </div>
  );
}
