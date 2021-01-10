import React, { PureComponent, MouseEvent } from "react";
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

type Props = RecordProps & { recordInfo: RecordInfo };

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

export default class PageActions extends PureComponent<Props, unknown> {
  constructor(props: Props) {
    super(props);
    this.fsOpen = this.fsOpen.bind(this);
  }

  fsOpen(event: MouseEvent) {
    event.preventDefault();
    loadData(
      "/browsefs",
      { path: this.props.record.path, alt: this.props.record.alt },
      { method: "POST" }
    ).then((resp) => {
      if (!resp.okay) {
        alert(trans("ERROR_CANNOT_BROWSE_FS"));
      }
    }, bringUpDialog);
  }

  render() {
    const urlPath = getUrlRecordPathWithAlt(
      this.props.record.path,
      this.props.record.alt
    );

    const { recordInfo } = this.props;

    const title = recordInfo.is_attachment
      ? trans("ATTACHMENT_ACTIONS")
      : trans("PAGE_ACTIONS");

    return (
      <div className="section">
        <h3>{title}</h3>
        <ul className="nav">
          <li key="edit">
            <Link to={`${urlPath}/edit`}>
              {recordInfo.is_attachment
                ? trans("EDIT_METADATA")
                : trans("EDIT")}
            </Link>
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
              <a href="#" onClick={this.fsOpen}>
                {getBrowseButtonTitle()}
              </a>
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
}
