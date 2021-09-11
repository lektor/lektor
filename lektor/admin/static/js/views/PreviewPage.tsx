import React, {
  SyntheticEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  fsPathFromAdminObservedPath,
  getCanonicalUrl,
  urlPathsConsideredEqual,
} from "../utils";
import { loadData } from "../fetch";
import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import { showErrorDialog } from "../error-dialog";
import { useHistory } from "react-router";

function getIframePath(iframe: HTMLIFrameElement): string | null {
  const location = iframe.contentWindow?.location;
  return !location || location.href === "about:blank"
    ? null
    : fsPathFromAdminObservedPath(location.pathname);
}

export default function PreviewPage({ record }: Pick<RecordProps, "record">) {
  const iframe = useRef<HTMLIFrameElement | null>(null);
  const [pageUrl, setPageUrl] = useState<string | null>(null);
  const [pageUrlPath, setPageUrlPath] = useState<string | null>(null);
  const history = useHistory();

  const { path, alt } = record;

  useEffect(() => {
    let ignore = false;

    loadData("/previewinfo", { path, alt }).then((resp) => {
      if (!ignore) {
        setPageUrl(resp.url);
        setPageUrlPath(getUrlRecordPath(path, alt));
      }
    }, showErrorDialog);

    return () => {
      ignore = true;
    };
  }, [alt, path]);

  useEffect(() => {
    const frame = iframe.current;
    const intendedPath =
      pageUrlPath === getUrlRecordPath(path, alt) ? pageUrl : null;
    if (frame && intendedPath) {
      const framePath = getIframePath(frame);

      if (!urlPathsConsideredEqual(intendedPath, framePath)) {
        frame.src = getCanonicalUrl(intendedPath);
      }
    }
  });

  const onFrameNavigated = useCallback(
    (event: SyntheticEvent<HTMLIFrameElement>) => {
      const framePath = getIframePath(event.currentTarget);
      if (framePath !== null) {
        loadData("/matchurl", { url_path: framePath }).then((resp) => {
          if (resp.exists) {
            const urlPath = getUrlRecordPath(resp.path, resp.alt);
            history.push(pathToAdminPage("preview", urlPath));
          }
        }, showErrorDialog);
      }
    },
    [history]
  );

  return (
    <div className="preview">
      <iframe ref={iframe} onLoad={onFrameNavigated} />
    </div>
  );
}
