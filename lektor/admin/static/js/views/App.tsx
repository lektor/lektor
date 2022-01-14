import React, { useReducer } from "react";

import Header from "../header/Header";
import Sidebar from "../sidebar/Sidebar";
import DialogSlot from "../components/DialogSlot";
import ServerStatus from "../components/ServerStatus";
import { RecordProps } from "../components/RecordComponent";
import ErrorDialog from "../components/ErrorDialog";

import EditPage from "./edit/EditPage";
import DeletePage from "./delete/DeletePage";
import PreviewPage from "./PreviewPage";
import AddChildPage from "./add-child-page/AddChildPage";
import AddAttachmentPage from "./AddAttachmentPage";

const mainComponentForPage = {
  edit: EditPage,
  delete: DeletePage,
  preview: PreviewPage,
  "add-child": AddChildPage,
  upload: AddAttachmentPage,
} as const;

export default function App({ page, record }: RecordProps) {
  const [sidebarIsActive, toggleSidebar] = useReducer((v) => !v, false);
  const MainComponent = mainComponentForPage[page];
  return (
    <>
      <Header
        sidebarIsActive={sidebarIsActive}
        toggleSidebar={toggleSidebar}
        page={page}
        record={record}
      />
      <ErrorDialog />
      <DialogSlot page={page} record={record} />
      <div className="container">
        <div
          className={
            sidebarIsActive
              ? "block-offcanvas row active"
              : "block-offcanvas row"
          }
        >
          <nav className="sidebar col-md-2 col-sm-3">
            <Sidebar page={page} record={record} />
          </nav>
          <div className="main col-md-10 col-sm-9">
            <MainComponent record={record} />
          </div>
        </div>
      </div>
      <ServerStatus />
    </>
  );
}
