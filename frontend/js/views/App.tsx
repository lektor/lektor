import React, { useContext, useEffect, useReducer, useState } from "react";

import Header from "../header/Header";
import Sidebar from "../sidebar/Sidebar";
import DialogSlot from "../components/DialogSlot";
import ServerStatus from "../components/ServerStatus";
import ErrorDialog from "../components/ErrorDialog";
import { useGoToAdminPage } from "../components/use-go-to-admin-page";

import EditPage from "./edit/EditPage";
import DeletePage from "./delete/DeletePage";
import PreviewPage from "./PreviewPage";
import AddChildPage from "./add-child-page/AddChildPage";
import AddAttachmentPage from "./AddAttachmentPage";
import { PageContext } from "../context/page-context";
import { useRecord } from "../context/record-context";

import {
  installShortcutKeyListener,
  setShortcutHandler,
  ShortcutAction,
} from "../shortcut-keys";
import {
  loadAppSettings,
  saveAppSettings,
  AppSettingsContext,
} from "../context/appsettings-context";

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
  const [appSettings, setAppSettings] = useState(loadAppSettings());
  const { path, alt } = useRecord();
  const goToAdminPage = useGoToAdminPage();
  const MainComponent = mainComponentForPage[page];

  useEffect(() => {
    saveAppSettings(appSettings);
    return installShortcutKeyListener(appSettings.shortcutKeyMap);
  }, [appSettings]);

  useEffect(() => {
    const cleanup = [
      setShortcutHandler(ShortcutAction.Edit, () =>
        goToAdminPage("edit", path, alt)
      ),
      setShortcutHandler(ShortcutAction.Preview, () =>
        goToAdminPage("preview", path, alt)
      ),
    ];
    return () => cleanup.forEach((cb) => cb());
  }, [path, alt, goToAdminPage]);

  return (
    <AppSettingsContext.Provider value={appSettings}>
      <Header sidebarIsActive={sidebarIsActive} toggleSidebar={toggleSidebar} />
      <ErrorDialog />
      <DialogSlot setAppSettings={setAppSettings} />
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
    </AppSettingsContext.Provider>
  );
}
