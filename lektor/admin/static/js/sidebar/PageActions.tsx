import React, { MouseEvent, memo, useCallback } from "react";
import {
  getUrlRecordPathWithAlt,
  RecordProps,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { RecordInfo } from "../components/types";
import { trans } from "../i18n";
import { getPlatform } from "../utils";
import { loadData } from "../fetch";
import { bringUpDialog } from "../richPromise";
import LinkWithHotkey from "../components/LinkWithHotkey";

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

function BrowseFSLink({ record }: Pick<RecordProps, "record">) {
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
      }, bringUpDialog);
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
}: RecordProps & { recordInfo: RecordInfo }) {
  const urlPath = getUrlRecordPathWithAlt(record.path, record.alt);

  return (
    <div className="section">
      <h3>
        {recordInfo.is_attachment
          ? trans("ATTACHMENT_ACTIONS")
          : trans("PAGE_ACTIONS")}
      </h3>
      <ul className="nav">
        <li key="edit">
          <LinkWithHotkey to={`${urlPath}/edit`} shortcut={editKey}>
            {recordInfo.is_attachment ? trans("EDIT_METADATA") : trans("EDIT")}
          </LinkWithHotkey>
        </li>
        {recordInfo.can_be_deleted && (
          <li key="delete">
            <Link to={`${urlPath}/delete`}>{trans("DELETE")}</Link>
          </li>
        )}
        <li key="preview">
          <Link to={`${urlPath}/preview`}>{trans("PREVIEW")}</Link>
        </li>
        {recordInfo.exists && (
          <li key="fs-open">
            <BrowseFSLink record={record} />
          </li>
        )}
        {recordInfo.can_have_children && (
          <li key="add-child">
            <Link to={`${urlPath}/add-child`}>{trans("ADD_CHILD_PAGE")}</Link>
          </li>
        )}
        {recordInfo.can_have_attachments && (
          <li key="add-attachment">
            <Link to={`${urlPath}/upload`}>{trans("ADD_ATTACHMENT")}</Link>
          </li>
        )}
      </ul>
    </div>
  );
}

export default memo(PageActions);
