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
} & RecordProps): JSX.Element {
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
          <BreadCrumbs page={page} record={record} />
          <div>
            <GlobalActions record={record} />
          </div>
        </div>
      </div>
    </header>
  );
}
