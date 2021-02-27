import React, { Component, ChangeEvent, ReactNode } from "react";
import {
  getUrlRecordPathWithAlt,
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import { getParentFsPath } from "../utils";
import { loadData } from "../fetch";
import { trans, trans_fallback, trans_format, trans_obj } from "../i18n";
import hub from "../hub";
import { AttachmentsChangedEvent } from "../events";
import { bringUpDialog } from "../richPromise";
import { RecordInfo } from "../components/types";

type State = {
  recordInfo: RecordInfo | null;
  deleteMasterRecord: boolean;
};

class DeletePage extends Component<RecordProps, State> {
  constructor(props: RecordProps) {
    super(props);

    this.state = {
      recordInfo: null,
      deleteMasterRecord: true,
    };

    this.cancelDelete = this.cancelDelete.bind(this);
    this.deleteRecord = this.deleteRecord.bind(this);
    this.onDeleteAllAltsChange = this.onDeleteAllAltsChange.bind(this);
  }

  componentDidMount() {
    this.syncDialog();
  }

  componentDidUpdate(prevProps: RecordProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.syncDialog();
    }
  }

  syncDialog() {
    loadData("/recordinfo", { path: this.props.record.path }).then((resp) => {
      this.setState({
        recordInfo: resp,
        deleteMasterRecord: this.isPrimary(),
      });
    }, bringUpDialog);
  }

  deleteRecord() {
    const path = this.props.record.path;
    const parent = getParentFsPath(path || "");
    const targetPath =
      parent === null
        ? "root"
        : getUrlRecordPathWithAlt(parent, this.props.record.alt);

    loadData(
      "/deleterecord",
      {
        path: path,
        alt: this.props.record.alt,
        delete_master: this.state.deleteMasterRecord ? "1" : "0",
      },
      { method: "POST" }
    ).then(() => {
      if (this.state.recordInfo?.is_attachment) {
        hub.emit(new AttachmentsChangedEvent(parent));
      }
      this.props.history.push(pathToAdminPage("edit", targetPath));
    }, bringUpDialog);
  }

  cancelDelete() {
    const urlPath = getUrlRecordPathWithAlt(
      this.props.record.path,
      this.props.record.alt
    );
    this.props.history.push(pathToAdminPage("edit", urlPath));
  }

  onDeleteAllAltsChange(event: ChangeEvent<HTMLInputElement>) {
    this.setState({
      deleteMasterRecord: event.target.value === "1",
    });
  }

  isPrimary() {
    return this.props.record.alt === "_primary";
  }

  render() {
    const ri = this.state.recordInfo;

    if (!ri || !ri.can_be_deleted) {
      return null;
    }

    const elements: ReactNode[] = [];
    const alts: ReactNode[] = [];
    const currentRecordAlternative = this.props.record.alt;
    const altInfo = ri.alts.find((a) => a.alt === currentRecordAlternative);
    const altCount = ri.alts.filter((a) => a.exists).length;

    if (altCount > 1 && currentRecordAlternative === "_primary") {
      ri.alts.forEach((item) => {
        if (!item.exists) {
          return;
        }
        let title = trans_obj(item.name_i18n);
        if (item.is_primary) {
          title += " (" + trans("PRIMARY_ALT") + ")";
        } else if (item.primary_overlay) {
          title += " (" + trans("PRIMARY_OVERLAY") + ")";
        }
        alts.push(<li key={item.alt}>{title}</li>);
      });
      elements.push(
        <p key="alt-warning">{trans("DELETE_PRIMARY_ALT_INFO")}</p>
      );
      elements.push(
        <ul key="delete-all-alts">
          <li>
            <label>
              <input
                type="radio"
                value="1"
                checked={this.state.deleteMasterRecord}
                onChange={this.onDeleteAllAltsChange}
              />{" "}
              {trans(
                ri.is_attachment
                  ? "DELETE_ALL_ATTACHMENT_ALTS"
                  : "DELETE_ALL_PAGE_ALTS"
              )}
            </label>
          </li>
          <li>
            <label>
              <input
                type="radio"
                value="0"
                checked={!this.state.deleteMasterRecord}
                onChange={this.onDeleteAllAltsChange}
              />{" "}
              {trans(
                ri.is_attachment
                  ? "DELETE_ONLY_PRIMARY_ATTACHMENT_ALT"
                  : "DELETE_ONLY_PRIMARY_PAGE_ALT"
              )}
            </label>
          </li>
        </ul>
      );
    }

    let label = trans_fallback(ri.label_i18n, ri.id);
    if (currentRecordAlternative !== "_primary" && altInfo !== undefined) {
      label += " (" + trans_obj(altInfo.name_i18n) + ")";
    }

    return (
      <div>
        <h2>{trans_format("DELETE_RECORD", label)}</h2>
        {ri.is_attachment ? (
          <p>
            {this.isPrimary()
              ? trans("DELETE_ATTACHMENT_PROMPT")
              : trans("DELETE_ATTACHMENT_ALT_PROMPT")}{" "}
          </p>
        ) : (
          <p>
            {this.isPrimary()
              ? trans("DELETE_PAGE_PROMPT")
              : trans("DELETE_PAGE_ALT_PROMPT")}{" "}
            {ri.children.length > 0 && this.isPrimary()
              ? trans("DELETE_PAGE_CHILDREN_WARNING")
              : null}
          </p>
        )}
        {elements}
        {this.state.deleteMasterRecord && alts.length > 0 && (
          <div>
            <h4>{trans("ALTS_TO_BE_DELETED")}</h4>
            <ul>{alts}</ul>
          </div>
        )}
        {this.state.deleteMasterRecord && ri.children.length > 0 && (
          <div>
            <h4>{trans("CHILD_PAGES_TO_BE_DELETED")}</h4>
            <ul>
              {ri.children.map((child) => (
                <li key={child.id}>{trans_obj(child.label_i18n)}</li>
              ))}
            </ul>
          </div>
        )}
        {this.state.deleteMasterRecord && ri.attachments.length > 0 && (
          <div>
            <h4>{trans("ATTACHMENTS_TO_BE_DELETED")}</h4>
            <ul>
              {ri.attachments.map((atch) => (
                <li key={atch.id}>
                  {atch.id} ({atch.type})
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={this.deleteRecord}
          >
            {trans("YES_DELETE")}
          </button>
          <button
            type="button"
            className="btn btn-secondary border"
            onClick={this.cancelDelete}
          >
            {trans("NO_CANCEL")}
          </button>
        </div>
      </div>
    );
  }
}

export default DeletePage;
