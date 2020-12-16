import React, { ReactNode, useState } from "react";
import { Route, useRouteMatch } from "react-router-dom";

import BreadCrumbs from "../components/BreadCrumbs";
import Sidebar from "../components/Sidebar";
import DialogSlot from "../components/DialogSlot";
import ServerStatus from "../components/ServerStatus";

function Header({
  sidebarIsActive,
  toggleSidebar,
}: {
  sidebarIsActive: boolean;
  toggleSidebar: () => void;
}) {
  const fullPath = `${$LEKTOR_CONFIG.admin_root}/:path/:page`;
  const match = useRouteMatch(fullPath);

  const buttonClass = sidebarIsActive
    ? "navbar-toggle active"
    : "navbar-toggle";

  return (
    <header>
      <BreadCrumbs match={match}>
        <button type="button" className={buttonClass} onClick={toggleSidebar}>
          <span className="sr-only">Toggle navigation</span>
          <span className="icon-list" />
          <span className="icon-list" />
          <span className="icon-list" />
        </button>
      </BreadCrumbs>
    </header>
  );
}

export default function App(props: { children: ReactNode }) {
  const fullPath = `${$LEKTOR_CONFIG.admin_root}/:path/:page`;

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
      <Header sidebarIsActive={sidebarIsActive} toggleSidebar={toggleSidebar} />
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
