import React, { MouseEvent, memo, useCallback } from "react";
import { RecordPathDetails } from "../components/RecordComponent";
import Link from "../components/Link";
import { RecordInfo } from "../components/types";
import { trans } from "../i18n";
import { getPlatform } from "../utils";
import { loadData } from "../fetch";
import { showErrorDialog } from "../error-dialog";
import LinkWithHotkey from "../components/LinkWithHotkey";
import { adminPath } from "../components/use-go-to-admin-page";

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

function BrowseFSLink({ record }: { record: RecordPathDetails }) {
  const fsOpen = useCallback(
    (ev: MouseEvent) => {
      ev.preventDefault();
      loadData(
        "/browsefs",
        { path: record.path, alt: record.alt },
        { method: "POST" }
      ).then((resp) => {
        if (!resp.okay) {
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

function PageActions({
  record,
  recordInfo,
}: {
  record: RecordPathDetails;
  recordInfo: RecordInfo;
}) {
  const { path, alt } = record;

  return (
    <div className="section">
      <h3>
        {recordInfo.is_attachment
          ? trans("ATTACHMENT_ACTIONS")
          : trans("PAGE_ACTIONS")}
      </h3>
      <ul className="nav">
        <li key="edit">
          <LinkWithHotkey to={adminPath("edit", path, alt)} shortcut={editKey}>
            {recordInfo.is_attachment ? trans("EDIT_METADATA") : trans("EDIT")}
          </LinkWithHotkey>
        </li>
        {recordInfo.can_be_deleted && (
          <li key="delete">
            <Link to={adminPath("delete", path, alt)}>{trans("DELETE")}</Link>
          </li>
        )}
        <li key="preview">
          <Link to={adminPath("preview", path, alt)}>{trans("PREVIEW")}</Link>
        </li>
        {recordInfo.exists && (
          <li key="fs-open">
            <BrowseFSLink record={record} />
          </li>
        )}
        {recordInfo.can_have_children && (
          <li key="add-child">
            <Link to={adminPath("add-child", path, alt)}>
              {trans("ADD_CHILD_PAGE")}
            </Link>
          </li>
        )}
        {recordInfo.can_have_attachments && (
          <li key="add-attachment">
            <Link to={adminPath("upload", path, alt)}>
              {trans("ADD_ATTACHMENT")}
            </Link>
          </li>
        )}
      </ul>
    </div>
  );
}

export default memo(PageActions);
