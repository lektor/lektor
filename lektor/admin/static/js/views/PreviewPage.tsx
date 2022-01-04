import React, {
  SyntheticEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { getCanonicalUrl, trimSlashes, trimTrailingSlashes } from "../utils";
import { get } from "../fetch";
import { RecordProps } from "../components/RecordComponent";
import { showErrorDialog } from "../error-dialog";
import { useGoToAdminPage } from "../components/use-go-to-admin-page";

function fsPathFromAdminObservedPath(adminPath: string): string | null {
  const base = trimTrailingSlashes($LEKTOR_CONFIG.site_root);
  return adminPath.startsWith(base)
    ? `/${trimSlashes(adminPath.substr(base.length))}`
    : null;
}

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

    get("/previewinfo", { path, alt }).then(({ url }) => {
      if (!ignore) {
        setPageUrl(url);
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

      if (
        !framePath ||
        trimTrailingSlashes(intendedPath) !== trimTrailingSlashes(framePath)
      ) {
        frame.src = getCanonicalUrl(intendedPath);
      }
    }
  });

  const onFrameNavigated = useCallback(
    (event: SyntheticEvent<HTMLIFrameElement>) => {
      const framePath = getIframePath(event.currentTarget);
      if (framePath !== null) {
        get("/matchurl", { url_path: framePath }).then(
          ({ exists, alt, path }) => {
            if (exists) {
              goToAdminPage("preview", path, alt);
            }
          },
          showErrorDialog
        );
      }
    },
    [goToAdminPage]
  );

  return <iframe className="preview" ref={iframe} onLoad={onFrameNavigated} />;
}
