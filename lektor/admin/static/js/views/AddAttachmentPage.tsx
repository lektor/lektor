import React, { Component, createRef, RefObject } from "react";
import { RecordProps } from "../components/RecordComponent";
import hub from "../hub";
import { AttachmentsChangedEvent } from "../events";
import { getApiUrl } from "../utils";
import { loadData } from "../fetch";
import { trans, trans_format } from "../i18n";
import { bringUpDialog } from "../richPromise";

type NewAttachmentInfo = {
  label: string;
  can_upload: boolean;
};

type State = {
  newAttachmentInfo: NewAttachmentInfo | null;
  currentFiles: File[];
  isUploading: boolean;
  currentProgress: number;
};

class AddAttachmentPage extends Component<RecordProps, State> {
  fileInput: RefObject<HTMLInputElement>;

  constructor(props: RecordProps) {
    super(props);
    this.state = {
      newAttachmentInfo: null,
      currentFiles: [],
      isUploading: false,
      currentProgress: 0,
    };
    this.fileInput = createRef();
    this.onUploadProgress = this.onUploadProgress.bind(this);
    this.onUploadComplete = this.onUploadComplete.bind(this);
    this.onFileSelected = this.onFileSelected.bind(this);
    this.uploadFile = this.uploadFile.bind(this);
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
    loadData("/newattachment", { path: this.props.record.path }).then(
      (resp) => {
        this.setState({ newAttachmentInfo: resp });
      },
      bringUpDialog
    );
  }

  uploadFile() {
    this.fileInput.current?.click();
  }

  onUploadProgress(event: ProgressEvent) {
    const newProgress = Math.round((event.loaded * 100) / event.total);
    if (newProgress !== this.state.currentProgress) {
      this.setState({ currentProgress: newProgress });
    }
  }

  onUploadComplete() {
    this.setState({ isUploading: false, currentProgress: 100 }, () => {
      hub.emit(new AttachmentsChangedEvent(this.props.record.path));
    });
  }

  onFileSelected() {
    if (this.state.isUploading || !this.fileInput.current?.files) {
      return;
    }

    const files: File[] = Array.prototype.slice.call(
      this.fileInput.current.files,
      0
    );
    this.setState({ currentFiles: files, isUploading: true });

    const formData = new FormData();
    formData.append("path", this.props.record.path || "");

    files.forEach((file) => {
      formData.append("file", file, file.name);
    });

    const xhr = new XMLHttpRequest();
    xhr.open("POST", getApiUrl("/newattachment"));
    xhr.onload = this.onUploadComplete;
    xhr.onprogress = this.onUploadProgress;
    xhr.send(formData);
  }

  render() {
    const newAttachmentInfo = this.state.newAttachmentInfo;

    if (!newAttachmentInfo) {
      return null;
    }

    return (
      <div>
        <h2>{trans_format("ADD_ATTACHMENT_TO", newAttachmentInfo.label)}</h2>
        <p>{trans("ADD_ATTACHMENT_NOTE")}</p>
        <ul>
          {this.state.currentFiles.map((file) => (
            <li key={file.name}>
              {file.name} ({file.type})
            </li>
          ))}
        </ul>
        <p>
          {trans("PROGRESS")}: {this.state.currentProgress}%
        </p>
        <input
          type="file"
          ref={this.fileInput}
          multiple
          style={{ display: "none" }}
          onChange={this.onFileSelected}
        />
        <div className="actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={this.uploadFile}
          >
            {trans("UPLOAD")}
          </button>
        </div>
      </div>
    );
  }
}

export default AddAttachmentPage;
