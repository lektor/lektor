import React, { Component } from "react";
import {
  getUrlRecordPathWithAlt,
  pathToAdminPage,
  RecordProps,
} from "../../components/RecordComponent";
import { getParentFsPath } from "../../utils";
import { loadData } from "../../fetch";
import hub from "../../hub";
import { AttachmentsChangedEvent } from "../../events";
import { bringUpDialog } from "../../richPromise";
import { RecordInfo } from "../../components/types";
import { DeletableAttachments } from "./DeletableAttachments";
import { DeletableChildPages } from "./DeletableChildPages";
import { DeletableAlternatives } from "./DeletableAlternatives";
import { DeletePageActions } from "./DeletePageActions";
import { DeleteAllAltsChoice } from "./DeleteAllAltsChoice";
import { DeletePageHeader } from "./DeletePageHeader";

type State = {
  recordInfo: RecordInfo | null;
  deleteMasterRecord: boolean;
};

class DeletePage extends Component<RecordProps, State> {
  constructor(props: RecordProps) {
    super(props);
    this.state = { recordInfo: null, deleteMasterRecord: true };
    this.cancelDelete = this.cancelDelete.bind(this);
    this.deleteRecord = this.deleteRecord.bind(this);
  }

  componentDidMount(): void {
    this.syncDialog();
  }

  componentDidUpdate(prevProps: RecordProps): void {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.syncDialog();
    }
  }

  syncDialog(): void {
    loadData("/recordinfo", { path: this.props.record.path }).then(
      (recordInfo) => {
        this.setState({
          recordInfo,
          deleteMasterRecord: this.props.record.alt === "_primary",
        });
      },
      bringUpDialog
    );
  }

  deleteRecord(): void {
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

  cancelDelete(): void {
    const urlPath = getUrlRecordPathWithAlt(
      this.props.record.path,
      this.props.record.alt
    );
    this.props.history.push(pathToAdminPage("edit", urlPath));
  }

  render(): JSX.Element | null {
    const { deleteMasterRecord, recordInfo } = this.state;

    if (!recordInfo || !recordInfo.can_be_deleted) {
      return null;
    }

    const currentAlt = this.props.record.alt;
    const hasAlts = recordInfo.alts.filter((a) => a.exists).length > 1;

    return (
      <div>
        <DeletePageHeader recordInfo={recordInfo} currentAlt={currentAlt} />
        {hasAlts && currentAlt === "_primary" && (
          <DeleteAllAltsChoice
            deleteMasterRecord={deleteMasterRecord}
            setDeleteMasterRecord={(deleteMasterRecord) => {
              this.setState({ deleteMasterRecord });
            }}
            isAttachment={recordInfo.is_attachment}
          />
        )}
        {deleteMasterRecord && (
          <>
            {hasAlts && currentAlt === "_primary" && (
              <DeletableAlternatives recordInfo={recordInfo} />
            )}
            {recordInfo.children.length > 0 && (
              <DeletableChildPages recordInfo={recordInfo} />
            )}
            {recordInfo.attachments.length > 0 && (
              <DeletableAttachments recordInfo={recordInfo} />
            )}
          </>
        )}

        <DeletePageActions
          deleteRecord={this.deleteRecord}
          cancelDelete={this.cancelDelete}
        />
      </div>
    );
  }
}

export default DeletePage;