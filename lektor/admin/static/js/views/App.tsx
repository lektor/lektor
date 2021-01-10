import React, { ReactNode, useState } from "react";
import { useHistory } from "react-router-dom";

import BreadCrumbs from "../components/BreadCrumbs";
import Sidebar from "../components/Sidebar";
import DialogSlot from "../components/DialogSlot";
import ServerStatus from "../components/ServerStatus";

type Params = { page: string; path: string };

function Header({
  params,
  sidebarIsActive,
  toggleSidebar,
}: {
  params: Params;
  sidebarIsActive: boolean;
  toggleSidebar: () => void;
}) {
  const buttonClass = sidebarIsActive
    ? "navbar-toggle active"
    : "navbar-toggle";

  return (
    <header>
      <BreadCrumbs match={{ params }}>
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

export default function App({
  children,
  params,
}: {
  children: ReactNode;
  params: Params;
}) {
  const history = useHistory();
  const routeProps = { match: { params }, history };

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
      <Header
        params={params}
        sidebarIsActive={sidebarIsActive}
        toggleSidebar={toggleSidebar}
      />
      <div className="editor container">
        <DialogSlot {...routeProps} />
        <div className={sidebarClasses}>
          <nav className="sidebar col-md-2 col-sm-3 sidebar-offcanvas">
            <Sidebar {...routeProps} />
          </nav>
          <div className="view col-md-10 col-sm-9">{children}</div>
        </div>
      </div>
    </div>
  );
}
