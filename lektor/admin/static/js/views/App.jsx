import React, { useState } from "react";
import { Route, useRouteMatch } from "react-router-dom";

import BreadCrumbs from "../components/BreadCrumbs";
import Sidebar from "../components/Sidebar";
import DialogSlot from "../components/DialogSlot";
import ServerStatus from "../components/ServerStatus";

function Header(props) {
  const match = useRouteMatch();

  const buttonClass = props.sidebarIsActive
    ? "navbar-toggle active"
    : "navbar-toggle";

  return (
    <header>
      <BreadCrumbs match={match}>
        <button
          type="button"
          className={buttonClass}
          onClick={props.toggleSidebar}
        >
          <span className="sr-only">Toggle navigation</span>
          <span className="icon-list" />
          <span className="icon-list" />
          <span className="icon-list" />
        </button>
      </BreadCrumbs>
    </header>
  );
}

function App(props) {
  const fullPath = `${props.match.path}/:path/:page`;
  const [sidebarIsActive, setSidebarIsActive] = useState(false);

  function toggleSidebar() {
    setSidebarIsActive(!sidebarIsActive);
  }
  const baseSidebarClasses =
    "sidebar-block block-offcanvas block-offcanvas-left";
  const sidebarClasses = sidebarIsActive
    ? baseSidebarClasses + " active"
    : baseSidebarClasses;

  return (
    <div className="application">
      <ServerStatus />
      <Route path={fullPath}>
        <Header
          sidebarIsActive={sidebarIsActive}
          toggleSidebar={toggleSidebar}
        />
      </Route>
      <div className="editor container">
        <Route path={fullPath} component={DialogSlot} />
        <div className={sidebarClasses}>
          <nav className="sidebar col-md-2 col-sm-3 sidebar-offcanvas">
            <Route path={fullPath} component={Sidebar} />
          </nav>
          <div className="view col-md-10 col-sm-9">{props.children}</div>
        </div>
      </div>
    </div>
  );
}

export default App;
