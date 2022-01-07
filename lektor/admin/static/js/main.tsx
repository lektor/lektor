import React from "react";
import ReactDOM from "react-dom";
import { ExtractRouteParams, RouteComponentProps } from "react-router";
import { BrowserRouter, Redirect, Route, Switch } from "react-router-dom";
import { setCurrentLanguage } from "./i18n";
import {
  PAGE_NAMES,
  PageName,
  useRecordAlt,
} from "./components/RecordComponent";

import "font-awesome/css/font-awesome.css";

import App from "./views/App";
import { adminPath } from "./components/use-go-to-admin-page";
import { trimSlashes } from "./utils";

type PagePath = `${string}/:recordPath*`;

interface PageProps
  extends RouteComponentProps<ExtractRouteParams<PagePath, string>> {
  page: PageName;
}

function pagePath(page: PageName): PagePath {
  const admin_root = $LEKTOR_CONFIG.admin_root;
  return `${admin_root}/${page}/:recordPath*`;
}

function Page({ match, page }: PageProps) {
  const { recordPath } = match.params;
  const record = {
    path: `/${trimSlashes(decodeURIComponent(recordPath ?? ""))}`,
    alt: useRecordAlt(),
  };

  return <App page={page} record={record} />;
}

function Main() {
  return (
    <BrowserRouter>
      <Switch>
        {PAGE_NAMES.map((page) => (
          <Route
            path={pagePath(page)}
            key={page}
            render={(props) => <Page {...props} page={page} />}
          />
        ))}
        <Route>
          <Redirect to={adminPath("edit", "/", "_primary")} />
        </Route>
      </Switch>
    </BrowserRouter>
  );
}

const dash = document.getElementById("dash");
if (dash) {
  setCurrentLanguage($LEKTOR_CONFIG.lang);
  ReactDOM.render(<Main />, dash);
}
