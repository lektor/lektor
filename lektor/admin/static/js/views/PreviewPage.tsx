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
import { RecordProps } from "../components/RecordComponent";
import { showErrorDialog } from "../error-dialog";
import { useGoToAdminPage } from "../components/use-go-to-admin-page";

function getIframePath(iframe: HTMLIFrameElement): string | null {
  const location = iframe.contentWindow?.location;
  return !location || location.href === "about:blank"
    ? null
    : fsPathFromAdminObservedPath(location.pathname);
}

export default function PreviewPage({
  record,
}: Pick<RecordProps, "record">): JSX.Element {
  const iframe = useRef<HTMLIFrameElement | null>(null);
  const [pageUrl, setPageUrl] = useState<string | null>(null);
  // This contains the path and alt of the page that we fetched the preview info for.
  // It's used to check whether we need to update the iframe src attribute.
  const [pageUrlPath, setPageUrlPath] = useState<string | null>(null);
  const goToAdminPage = useGoToAdminPage();

  const { path, alt } = record;

  useEffect(() => {
    let ignore = false;

    loadData("/previewinfo", { path, alt }).then((resp) => {
      if (!ignore) {
        setPageUrl(resp.url);
        setPageUrlPath(`${path}${alt}`);
      }
    }, showErrorDialog);

    return () => {
      ignore = true;
    };
  }, [alt, path]);

  useEffect(() => {
    const frame = iframe.current;
    const intendedPath = pageUrlPath === `${path}${alt}` ? pageUrl : null;
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
            goToAdminPage("preview", resp.path, resp.alt);
          }
        }, showErrorDialog);
      }
    },
    [goToAdminPage]
  );

  return (
    <div className="preview">
      <iframe ref={iframe} onLoad={onFrameNavigated} />
    </div>
  );
}
