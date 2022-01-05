import React, { useMemo } from "react";
import ReactDOM from "react-dom";
import { BrowserRouter, Redirect, useRouteMatch } from "react-router-dom";
import { setCurrentLanguage } from "./i18n";

import "font-awesome/css/font-awesome.css";

// route targets
import App from "./views/App";
import EditPage from "./views/edit/EditPage";
import DeletePage from "./views/delete/DeletePage";
import PreviewPage from "./views/PreviewPage";
import AddChildPage from "./views/add-child-page/AddChildPage";
import AddAttachmentPage from "./views/AddAttachmentPage";
import { getRecordDetails } from "./components/RecordComponent";
import { adminPath } from "./components/use-go-to-admin-page";

setCurrentLanguage($LEKTOR_CONFIG.lang);

function getMainComponent(page: string) {
  if (page === "edit") {
    return EditPage;
  } else if (page === "delete") {
    return DeletePage;
  } else if (page === "preview") {
    return PreviewPage;
  } else if (page === "add-child") {
    return AddChildPage;
  } else if (page === "upload") {
    return AddAttachmentPage;
  }
  return null;
}

function Main() {
  const match = useRouteMatch<{ path: string; page: string }>(
    `${$LEKTOR_CONFIG.admin_root}/:path/:page`
  );
  // useRouteMatch returns a new object on each render, so we need to get the
  // primitive string values here to memoize.
  const urlPath = match?.params.path;
  const page = match?.params.page;

  const record = useMemo(() => {
    if (!urlPath) {
      return null;
    }
    return getRecordDetails(urlPath);
  }, [urlPath]);

  if (!page) {
    return <Redirect to={adminPath("edit", "/", "_primary")} />;
  }
  const Component = getMainComponent(page);
  if (!Component || record === null) {
    return <Redirect to={adminPath("edit", "/", "_primary")} />;
  }
  return (
    <App page={page} record={record}>
      <Component record={record} />
    </App>
  );
}

const dash = document.getElementById("dash");

if (dash) {
  ReactDOM.render(
    <BrowserRouter>
      <Main />
    </BrowserRouter>,
    dash
  );
}
