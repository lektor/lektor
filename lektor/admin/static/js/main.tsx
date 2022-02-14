import React, { useMemo } from "react";
import ReactDOM from "react-dom";
import {
  BrowserRouter,
  Redirect,
  useLocation,
  useRouteMatch,
} from "react-router-dom";
import { setCurrentLanguage } from "./i18n";
import { RecordContext, RecordPathDetails } from "./context/record-context";

import App from "./views/App";
import { adminPath } from "./components/use-go-to-admin-page";

import "font-awesome/css/font-awesome.css";
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
  const root = $LEKTOR_CONFIG.admin_root;
  const page = useRouteMatch<{ page: string }>(`${root}/:page`)?.params.page;
  if (!isPageName(page)) {
    return <Redirect to={adminPath("edit", "/", "_primary")} />;
  }
  return <Page page={page} />;
}

const dash = document.getElementById("dash");
if (dash) {
  setCurrentLanguage($LEKTOR_CONFIG.lang);
  ReactDOM.render(
    <BrowserRouter>
      <Main />
    </BrowserRouter>,
    dash
  );
}
