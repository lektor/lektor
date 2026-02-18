import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { trimLeadingSlashes, trimTrailingSlashes } from "../utils";
import { get } from "../fetch";
import { useRecord } from "../context/record-context";
import { showErrorDialog } from "../error-dialog";
import { useGoToAdminPage } from "../components/use-go-to-admin-page";

function getSiteRootUrl() {
  const site_root = `/${trimLeadingSlashes($LEKTOR_CONFIG.site_root)}`;
  const absRootUrl = new URL(site_root, document.baseURI).href;
  return trimTrailingSlashes(absRootUrl);
}

function usePreviewUrl(siteRootUrl: string): string {
  const { path, alt } = useRecord();
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

export default function PreviewPage(): React.JSX.Element {
  const siteRootUrl = useMemo(() => getSiteRootUrl(), []);
  const previewUrl = usePreviewUrl(siteRootUrl);
  const iframe = useRef<HTMLIFrameElement | null>(null);
  const goToAdminPage = useGoToAdminPage();

  useEffect(() => {
    const location = iframe.current?.contentWindow?.location;
    if (location && location.href !== previewUrl) {
      location.replace(previewUrl);
    }
  }, [previewUrl]);

  const onLoad = useCallback(() => {
    const contentWindow = iframe.current?.contentWindow;
    if (contentWindow) {
      // Note that cross-origin security restrictions prevent us
      // from being able to inspect or manipulate pages from
      // other origins, so this will only work when the iframe is
      // previewing one of our pages.
      try {
        // Pass keydown events on to parent window
        // This is an attempt to ensure that hotkeys like Ctl-e work
        // even when the iframe has the focus.
        contentWindow.addEventListener("keydown", (ev: KeyboardEvent) => {
          const clone = new KeyboardEvent(ev.type, ev);
          // eslint-disable-next-line @typescript-eslint/no-unused-expressions
          window.dispatchEvent(clone) || ev.preventDefault();
        });

        const href = contentWindow.location.href;
        if (href && href !== previewUrl) {
          // Iframe has been navigated to a new page (e.g. user clicked link)
          if (href.startsWith(`${siteRootUrl}/`)) {
            // Attempt to move Admin UI to new page
            const url_path = href.substring(siteRootUrl.length);
            get("/matchurl", { url_path }).then(({ exists, alt, path }) => {
              if (exists) {
                goToAdminPage("preview", path, alt);
              }
            }, showErrorDialog);
          }
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === "SecurityError") {
          // Ignore exceptions having to do with cross-origin restrictions
        } else {
          throw e;
        }
      }
    }
  }, [goToAdminPage, previewUrl, siteRootUrl]);

  return <iframe className="preview" ref={iframe} onLoad={onLoad} />;
}
