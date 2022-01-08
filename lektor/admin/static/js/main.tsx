import React from "react";
import ReactDOM from "react-dom";
import { BrowserRouter, Redirect, Route, Switch } from "react-router-dom";
import { setCurrentLanguage } from "./i18n";
import { PAGE_NAMES, PageName, useRecord } from "./components/RecordComponent";

import "font-awesome/css/font-awesome.css";

import App from "./views/App";
import { adminPath } from "./components/use-go-to-admin-page";

function Page({ page }: { page: PageName }) {
  const record = useRecord();
  return <App page={page} record={record} />;
}

function Main() {
  const root = $LEKTOR_CONFIG.admin_root;

  return (
    <BrowserRouter>
      <Switch>
        {PAGE_NAMES.map((page) => {
          // XXX: When Path is not explicitly specified, it seems currently
          // to be inferred as the too-narrow type `${string}/edit`.
          // Maybe a @types/react bug?
          type Path = `${string}/${PageName}`;
          return (
            // eslint-disable-next-line @typescript-eslint/ban-types
            <Route<{}, Path> path={`${root}/${page}`} key={page}>
              <Page page={page} />
            </Route>
          );
        })}
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
