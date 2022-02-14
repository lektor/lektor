import React, { MouseEvent, memo, useCallback } from "react";
import { useRecord } from "../context/record-context";
import { RecordInfo } from "../components/types";
import { trans } from "../i18n";
import { getPlatform } from "../utils";
import { post } from "../fetch";
import { showErrorDialog } from "../error-dialog";
import AdminLinkWithHotkey from "../components/AdminLinkWithHotkey";
import AdminLink from "../components/AdminLink";

const getBrowseButtonTitle = () => {
  const platform = getPlatform();
  if (platform === "mac") {
    return trans("BROWSE_FS_MAC");
  } else if (platform === "windows") {
    return trans("BROWSE_FS_WINDOWS");
  } else {
    return trans("BROWSE_FS");
  }
};

function BrowseFSLink() {
  const record = useRecord();
  const fsOpen = useCallback(
    (ev: MouseEvent) => {
      ev.preventDefault();
      post("/browsefs", record).then(({ okay }) => {
        if (!okay) {
          alert(trans("ERROR_CANNOT_BROWSE_FS"));
        }
      }, showErrorDialog);
    },
    [record]
  );
  return (
    <a href="#" onClick={fsOpen}>
      {getBrowseButtonTitle()}
    </a>
  );
}

const editKey = { key: "Control+e", mac: "Meta+e", preventDefault: true };

function PageActions({ recordInfo }: { recordInfo: RecordInfo }) {
  const { path, alt } = useRecord();

  return (
    <>
      <h3>
        {recordInfo.is_attachment
          ? trans("ATTACHMENT_ACTIONS")
          : trans("PAGE_ACTIONS")}
      </h3>
      <ul className="nav">
        <li key="edit">
          <AdminLinkWithHotkey
            page="edit"
            path={path}
            alt={alt}
            shortcut={editKey}
          >
            {recordInfo.is_attachment ? trans("EDIT_METADATA") : trans("EDIT")}
          </AdminLinkWithHotkey>
        </li>
        {recordInfo.can_be_deleted && (
          <li key="delete">
            <AdminLink page="delete" path={path} alt={alt}>
              {trans("DELETE")}
            </AdminLink>
          </li>
        )}
        <li key="preview">
          <AdminLink page="preview" path={path} alt={alt}>
            {trans("PREVIEW")}
          </AdminLink>
        </li>
        {recordInfo.exists && (
          <li key="fs-open">
            <BrowseFSLink />
          </li>
        )}
        {recordInfo.can_have_children && (
          <li key="add-child">
            <AdminLink page="add-child" path={path} alt={alt}>
              {trans("ADD_CHILD_PAGE")}
            </AdminLink>
          </li>
        )}
        {recordInfo.can_have_attachments && (
          <li key="add-attachment">
            <AdminLink page="upload" path={path} alt={alt}>
              {trans("ADD_ATTACHMENT")}
            </AdminLink>
          </li>
        )}
      </ul>
    </>
  );
}

export default memo(PageActions);
