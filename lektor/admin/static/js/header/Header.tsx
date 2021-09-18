import React from "react";
import { RecordProps } from "../components/RecordComponent";

import BreadCrumbs from "./BreadCrumbs";
import GlobalActions from "./GlobalActions";

export default function Header({
  sidebarIsActive,
  toggleSidebar,
  page,
  record,
}: {
  sidebarIsActive: boolean;
  toggleSidebar: () => void;
} & Pick<RecordProps, "record" | "page">) {
  const buttonClass = sidebarIsActive
    ? "navbar-toggle active"
    : "navbar-toggle";

  return (
    <header>
      <div className="container">
        <button type="button" className={buttonClass} onClick={toggleSidebar}>
          <span className="sr-only">Toggle navigation</span>
          <span className="icon-list" />
          <span className="icon-list" />
          <span className="icon-list" />
        </button>
        <div className="d-flex justify-content-between">
          <BreadCrumbs page={page} record={record} />
          <div className="global-actions">
            <GlobalActions record={record} />
          </div>
        </div>
      </div>
    </header>
  );
}
