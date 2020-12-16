import React from "react";
import ReactDOM from "react-dom";
import {
  BrowserRouter as Router,
  Redirect,
  useHistory,
  useRouteMatch,
} from "react-router-dom";
import { setCurrentLanguage } from "./i18n";

import "font-awesome/css/font-awesome.css";

// polyfill for internet explorer
import "event-source-polyfill";

// route targets
import App from "./views/App";
import EditPage from "./views/EditPage";
import DeletePage from "./views/DeletePage";
import PreviewPage from "./views/PreviewPage";
import AddChildPage from "./views/AddChildPage";
import AddAttachmentPage from "./views/AddAttachmentPage";

setCurrentLanguage($LEKTOR_CONFIG.lang);

function Main() {
  const root = $LEKTOR_CONFIG.admin_root;
  const fullPath = `${root}/:path/:page`;
  const match = useRouteMatch<{ path: string; page: string }>(fullPath);
  if (!match) {
    return <Redirect to={`${root}/root/edit`} />;
  }
  const { page, path } = match.params;
  let Component = null;
  if (page === "edit") {
    Component = EditPage;
  } else if (page === "delete") {
    Component = DeletePage;
  } else if (page === "preview") {
    Component = PreviewPage;
  } else if (page === "add-child") {
    Component = AddChildPage;
  } else if (page === "upload") {
    Component = AddAttachmentPage;
  }
  if (!Component) {
    return <Redirect to={`${root}/root/edit`} />;
  }
  const history = useHistory();

  const params = { path, page };
  return (
    <App params={params}>
      <Component match={{ params }} history={history} />
    </App>
  );
}

const dash = document.getElementById("dash");

if (dash) {
  ReactDOM.render(
    <Router>
      <Main />
    </Router>,
    dash
  );
}
