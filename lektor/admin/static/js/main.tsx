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
import { getRecordDetails } from "./components/RecordComponent";

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
  const root = $LEKTOR_CONFIG.admin_root;
  const fullPath = `${root}/:path/:page`;
  const match = useRouteMatch<{ path: string; page: string }>(fullPath);
  const history = useHistory();

  if (!match) {
    return <Redirect to={`${root}/root/edit`} />;
  }
  const { page, path } = match.params;
  const Component = getMainComponent(page);
  if (!Component) {
    return <Redirect to={`${root}/root/edit`} />;
  }

  const params = { path, page };
  return (
    <App params={params}>
      <Component
        match={{ params }}
        history={history}
        record={getRecordDetails(params.path)}
      />
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
