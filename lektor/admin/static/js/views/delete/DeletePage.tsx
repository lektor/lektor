import React, { Component } from "react";
import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../../components/RecordComponent";
import { getParentFsPath } from "../../utils";
import { loadData } from "../../fetch";
import { showErrorDialog } from "../../error-dialog";
import { RecordInfo } from "../../components/types";
import { DeletableAttachments } from "./DeletableAttachments";
import { DeletableChildPages } from "./DeletableChildPages";
import { DeletableAlternatives } from "./DeletableAlternatives";
import { DeletePageActions } from "./DeletePageActions";
import { DeleteAllAltsChoice } from "./DeleteAllAltsChoice";
import { DeletePageHeader } from "./DeletePageHeader";
import { dispatch } from "../../events";

type State = {
  recordInfo: RecordInfo | null;
  deleteMasterRecord: boolean;
};

type Props = Pick<RecordProps, "record" | "history">;

class DeletePage extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { recordInfo: null, deleteMasterRecord: true };
    this.cancelDelete = this.cancelDelete.bind(this);
    this.deleteRecord = this.deleteRecord.bind(this);
  }

  componentDidMount(): void {
    this.syncDialog();
  }

  componentDidUpdate(prevProps: Props): void {
    if (prevProps.record.path !== this.props.record.path) {
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
      showErrorDialog
    );
  }

  deleteRecord(): void {
    const path = this.props.record.path;
    const parent = getParentFsPath(path || "");
    const targetPath =
      parent === null
        ? "root"
        : getUrlRecordPath(parent, this.props.record.alt);

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
        dispatch("lektor-attachments-changed", parent ?? "");
      }
      this.props.history.push(pathToAdminPage("edit", targetPath));
    }, showErrorDialog);
  }

  cancelDelete(): void {
    const urlPath = getUrlRecordPath(
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
