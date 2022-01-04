import React, { ReactNode, useReducer } from "react";

import Header from "../header/Header";
import Sidebar from "../sidebar/Sidebar";
import DialogSlot from "../components/DialogSlot";
import ServerStatus from "../components/ServerStatus";
import { RecordPathDetails } from "../components/RecordComponent";
import ErrorDialog from "../components/ErrorDialog";

export default function App({
  children,
  page,
  record,
}: {
  children: ReactNode;
  page: string;
  record: RecordPathDetails;
}): JSX.Element {
  const [sidebarIsActive, toggleSidebar] = useReducer((v) => !v, false);

  const sidebarClasses = sidebarIsActive
    ? "sidebar-block block-offcanvas block-offcanvas-left row active"
    : "sidebar-block block-offcanvas block-offcanvas-left row";

  return (
    <>
      <Header
        sidebarIsActive={sidebarIsActive}
        toggleSidebar={toggleSidebar}
        page={page}
        record={record}
      />
      <div className="main-container container">
        <ErrorDialog />
        <div className={sidebarClasses}>
          <nav className="sidebar col-md-2 col-sm-3 sidebar-offcanvas">
            <Sidebar page={page} record={record} />
          </nav>
          <div className="main col-md-10 col-sm-9">{children}</div>
        </div>
      </div>
      <DialogSlot page={page} record={record} />
      <ServerStatus />
    </>
  );
}
