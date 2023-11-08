import React, { StrictMode, useMemo } from "react";
import { createRoot } from "react-dom/client";
import {
  Navigate,
  RouterProvider,
  createBrowserRouter,
  useLocation,
  useMatch,
} from "react-router-dom";
import { setCurrentLanguage } from "./i18n";
import { RecordContext, RecordPathDetails } from "./context/record-context";

import App from "./views/App";
import { adminPath } from "./components/use-go-to-admin-page";

/** Fonts */
import "font-awesome/css/font-awesome.css";
import "@fontsource/roboto-slab/400.css";
import "@fontsource/roboto-slab/700.css";

import "../scss/main.scss";
import { PageContext, PageName, isPageName } from "./context/page-context";
import { trimSlashes } from "./utils";

function Page({ page }: { page: PageName }) {
  const { search } = useLocation();
  const record = useMemo((): RecordPathDetails => {
    const params = new URLSearchParams(search);
    return {
      path: `/${trimSlashes(params.get("path") ?? "/")}`,
      alt: params.get("alt") ?? "_primary",
    };
  }, [search]);

  return (
    <PageContext.Provider value={page}>
      <RecordContext.Provider value={record}>
        <App />
      </RecordContext.Provider>
    </PageContext.Provider>
  );
}

function Main() {
  const page = useMatch(":page")?.params.page;
  if (!isPageName(page)) {
    return <Navigate to={adminPath("edit", "/", "_primary")} />;
  }
  return <Page page={page} />;
}

const dash = document.getElementById("dash");
if (dash) {
  setCurrentLanguage($LEKTOR_CONFIG.lang);

  const root = createRoot(dash);
  const router = createBrowserRouter(
    [
      {
        path: "/",
        element: <Navigate to={adminPath("edit", "/", "_primary")} />,
      },
      {
        path: "/:page",
        element: <Main />,
      },
    ],
    {
      basename: $LEKTOR_CONFIG.admin_root,
    },
  );

  let app = <RouterProvider router={router} />;
  if (process.env.NODE_ENV !== "production") {
    app = <StrictMode>{app}</StrictMode>;
  }
  root.render(app);
}
