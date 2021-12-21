import React from "react";
import ReactDOM from "react-dom";
import { BrowserRouter, Redirect, useRouteMatch } from "react-router-dom";
import { setCurrentLanguage } from "./i18n";
import { useRecordAlt } from "./components/RecordComponent";

import "font-awesome/css/font-awesome.css";

// route targets
import App from "./views/App";
import EditPage from "./views/edit/EditPage";
import DeletePage from "./views/delete/DeletePage";
import PreviewPage from "./views/PreviewPage";
import AddChildPage from "./views/add-child-page/AddChildPage";
import AddAttachmentPage from "./views/AddAttachmentPage";
import { adminPath } from "./components/use-go-to-admin-page";
import { trimSlashes } from "./utils";

setCurrentLanguage($LEKTOR_CONFIG.lang);

const componentForPage = new Map([
  ["edit", EditPage],
  ["delete", DeletePage],
  ["preview", PreviewPage],
  ["add-child", AddChildPage],
  ["upload", AddAttachmentPage],
]);

function NotFound() {
  return <Redirect to={adminPath("edit", "/", "_primary")} />;
}

function Main() {
  const match = useRouteMatch<{ path: string; page: string }>(
    `${$LEKTOR_CONFIG.admin_root}/:page/:path*`
  );
  const alt = useRecordAlt();

  if (!match) {
    return <NotFound />;
  }

  const page = decodeURIComponent(match.params.page);
  const PageComponent = componentForPage.get(page);
  if (!PageComponent) {
    return <NotFound />;
  }

  const path = `/${trimSlashes(decodeURIComponent(match.params.path ?? ""))}`;
  const record = { path, alt };

  return (
    <App page={page} record={record}>
      <PageComponent record={record} />
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
