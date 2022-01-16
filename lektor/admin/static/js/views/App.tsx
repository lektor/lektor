import React, { useContext, useReducer } from "react";

import Header from "../header/Header";
import Sidebar from "../sidebar/Sidebar";
import DialogSlot from "../components/DialogSlot";
import ServerStatus from "../components/ServerStatus";
import ErrorDialog from "../components/ErrorDialog";

import EditPage from "./edit/EditPage";
import DeletePage from "./delete/DeletePage";
import PreviewPage from "./PreviewPage";
import AddChildPage from "./add-child-page/AddChildPage";
import AddAttachmentPage from "./AddAttachmentPage";
import { PageContext } from "../context/page-context";

const mainComponentForPage = {
  edit: EditPage,
  delete: DeletePage,
  preview: PreviewPage,
  "add-child": AddChildPage,
  upload: AddAttachmentPage,
} as const;

export default function App() {
  const page = useContext(PageContext);

  const [sidebarIsActive, toggleSidebar] = useReducer((v) => !v, false);
  const MainComponent = mainComponentForPage[page];
  return (
    <>
      <Header sidebarIsActive={sidebarIsActive} toggleSidebar={toggleSidebar} />
      <ErrorDialog />
      <DialogSlot />
      <div className="container">
        <div
          className={
            sidebarIsActive
              ? "block-offcanvas row active"
              : "block-offcanvas row"
          }
        >
          <nav className="sidebar col-md-2 col-sm-3">
            <Sidebar />
          </nav>
          <div className="main col-md-10 col-sm-9">
            <MainComponent />
          </div>
        </div>
      </div>
      <ServerStatus />
    </>
  );
}
