import React, {
  SyntheticEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { trimLeadingSlashes, trimTrailingSlashes } from "../utils";
import { get } from "../fetch";
import { RecordPathDetails, useRecord } from "../context/record-context";
import { showErrorDialog } from "../error-dialog";
import { useGoToAdminPage } from "../components/use-go-to-admin-page";

function getSiteRootUrl() {
  const site_root = `/${trimLeadingSlashes($LEKTOR_CONFIG.site_root)}`;
  const absRootUrl = new URL(site_root, document.baseURI).href;
  return trimTrailingSlashes(absRootUrl);
}

function usePreviewUrl(
  { path, alt }: RecordPathDetails,
  siteRootUrl: string
): string {
  const [previewUrl, setPreviewUrl] = useState<string>("about:blank");

  useEffect(() => {
    let ignore = false;
    get("/previewinfo", { path, alt }).then(({ url }) => {
      if (!ignore) {
        setPreviewUrl(url ? siteRootUrl + url : "about:blank");
      }
    }, showErrorDialog);

    return () => {
      ignore = true;
    };
  }, [path, alt, siteRootUrl]);

  return previewUrl;
}

export default function PreviewPage(): JSX.Element {
  const record = useRecord();
  const siteRootUrl = useMemo(getSiteRootUrl, []);
  const previewUrl = usePreviewUrl(record, siteRootUrl);
  const iframe = useRef<HTMLIFrameElement | null>(null);
  const goToAdminPage = useGoToAdminPage();

  useEffect(() => {
    const location = iframe.current?.contentWindow?.location;
    if (location && location.href !== previewUrl) {
      location.replace(previewUrl);
    }
  }, [previewUrl]);

  const onFrameNavigated = useCallback(
    (event: SyntheticEvent<HTMLIFrameElement>) => {
      const location = event.currentTarget.contentWindow?.location;
      if (location && location.href !== previewUrl) {
        if (location.href.startsWith(`${siteRootUrl}/`)) {
          const url_path = location.href.substr(siteRootUrl.length);
          get("/matchurl", { url_path }).then(({ exists, alt, path }) => {
            if (exists) {
              goToAdminPage("preview", path, alt);
            }
          }, showErrorDialog);
        }
      }
    },
    [goToAdminPage, previewUrl, siteRootUrl]
  );

  return <iframe className="preview" ref={iframe} onLoad={onFrameNavigated} />;
}
