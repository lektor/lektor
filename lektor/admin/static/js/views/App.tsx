import React, { ReactNode, useState } from "react";
import { useHistory } from "react-router-dom";

import Header from "../header/Header";
import Sidebar from "../sidebar/Sidebar";
import DialogSlot from "../components/DialogSlot";
import ServerStatus from "../components/ServerStatus";
import { getRecordDetails, RecordProps } from "../components/RecordComponent";

export default function App({
  children,
  params,
}: {
  children: ReactNode;
  params: { page: string; path: string };
}) {
  const history = useHistory();
  const match = { params };
  const recordProps: RecordProps = {
    match,
    history,
    record: getRecordDetails(params.path),
  };

  const [sidebarIsActive, setSidebarIsActive] = useState(false);

  function toggleSidebar() {
    setSidebarIsActive(!sidebarIsActive);
  }
  const baseSidebarClasses =
    "sidebar-block block-offcanvas block-offcanvas-left row";
  const sidebarClasses = sidebarIsActive
    ? baseSidebarClasses + " active"
    : baseSidebarClasses;

  return (
    <div className="application">
      <ServerStatus />
      <Header
        sidebarIsActive={sidebarIsActive}
        toggleSidebar={toggleSidebar}
        {...recordProps}
      />
      <div className="editor container">
        <DialogSlot {...recordProps} />
        <div className={sidebarClasses}>
          <nav className="sidebar col-md-2 col-sm-3 sidebar-offcanvas">
            <Sidebar {...recordProps} />
          </nav>
          <div className="view col-md-10 col-sm-9">{children}</div>
        </div>
      </div>
    </div>
  );
}
