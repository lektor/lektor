import React, { useMemo } from "react";
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
import EditPage from "./views/edit/EditPage";
import DeletePage from "./views/delete/DeletePage";
import PreviewPage from "./views/PreviewPage";
import AddChildPage from "./views/add-child-page/AddChildPage";
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
  // useRouteMatch returns a new object on each render, so we need to get the
  // primitive string values here to memoize.
  const urlPath = match?.params.path;
  const page = match?.params.page;

  const record = useMemo(() => {
    if (!urlPath) {
      return null;
    }
    const { path, alt } = getRecordDetails(urlPath);
    if (path === null) {
      return null;
    }
    return { path, alt };
  }, [urlPath]);

  if (!page) {
    return <Redirect to={`${root}/root/edit`} />;
  }
  const Component = getMainComponent(page);
  if (!Component || record === null) {
    return <Redirect to={`${root}/root/edit`} />;
  }
  return (
    <App page={page} record={record}>
      <Component history={history} record={record} />
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
