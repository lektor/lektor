import React, { useCallback, useEffect } from "react";
import { useRecord } from "../context/record-context";
import { getCanonicalUrl, keyboardShortcutHandler } from "../utils";
import { get } from "../fetch";
import { trans } from "../i18n";
import { showErrorDialog } from "../error-dialog";
import { dispatch } from "../events";

const findFiles = () => dispatch("lektor-dialog", { type: "find-files" });
const refresh = () => dispatch("lektor-dialog", { type: "refresh" });
const publish = () => dispatch("lektor-dialog", { type: "publish" });

const onKeyPress = keyboardShortcutHandler(
  { key: "Control+g", mac: "Meta+g", preventDefault: true },
  findFiles
);

export default function GlobalActions(): JSX.Element {
  const record = useRecord();

  useEffect(() => {
    window.addEventListener("keydown", onKeyPress);
    return () => window.removeEventListener("keydown", onKeyPress);
  }, []);

  const returnToWebsite = useCallback(() => {
    get("/previewinfo", record).then(({ url }) => {
      window.location.href =
        url === null ? getCanonicalUrl("/") : getCanonicalUrl(url);
    }, showErrorDialog);
  }, [record]);

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
      <button
        type="button"
        className="btn btn-secondary border"
        onClick={returnToWebsite}
        title={trans("RETURN_TO_WEBSITE")}
      >
        <i className="fa fa-eye fa-fw" />
      </button>
    </div>
  );
}
