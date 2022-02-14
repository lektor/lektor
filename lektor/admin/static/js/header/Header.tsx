import React from "react";

import BreadCrumbs from "./BreadCrumbs";
import GlobalActions from "./GlobalActions";

export default function Header({
  sidebarIsActive,
  toggleSidebar,
}: {
  sidebarIsActive: boolean;
  toggleSidebar: () => void;
}): JSX.Element {
  return (
    <header>
      <div className="container">
        <button
          type="button"
          className={
            sidebarIsActive
              ? "fa fa-bars navbar-toggle active"
              : "fa fa-bars navbar-toggle"
          }
          onClick={toggleSidebar}
          aria-label="Toggle navigation"
        />
        <div className="d-flex justify-content-between">
          <BreadCrumbs />
          <div>
            <GlobalActions />
          </div>
        </div>
      </div>
    </header>
  );
}
