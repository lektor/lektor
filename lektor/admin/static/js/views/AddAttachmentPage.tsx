import React, { createRef, RefObject } from "react";
import RecordComponent, { RecordProps } from "../components/RecordComponent";
import hub from "../hub";
import { AttachmentsChangedEvent } from "../events";
import { getApiUrl } from "../utils";
import { loadData } from "../fetch";
import { trans } from "../i18n";
import { bringUpDialog } from "../richPromise";

type State = {
  newAttachmentInfo: null;
  currentFiles: File[];
  isUploading: boolean;
  currentProgress: number;
};

class AddAttachmentPage extends RecordComponent<unknown, State> {
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
    loadData("/newattachment", { path: this.getRecordPath() }).then((resp) => {
      this.setState({
        newAttachmentInfo: resp,
      });
    }, bringUpDialog);
  }

  uploadFile() {
    this.fileInput.current?.click();
  }

  onUploadProgress(event: ProgressEvent) {
    const newProgress = Math.round((event.loaded * 100) / event.total);
    if (newProgress !== this.state.currentProgress) {
      this.setState({
        currentProgress: newProgress,
      });
    }
  }

  onUploadComplete(resp) {
    this.setState(
      {
        isUploading: false,
        currentProgress: 100,
      },
      () => {
        hub.emit(
          new AttachmentsChangedEvent({
            recordPath: this.getRecordPath(),
            attachmentsAdded: resp.buckets.map((bucket) => {
              return bucket.stored_filename;
            }),
          })
        );
      }
    );
  }

  onFileSelected() {
    if (this.state.isUploading || !this.fileInput.current?.files) {
      return;
    }

    const files: File[] = Array.prototype.slice.call(
      this.fileInput.current.files,
      0
    );
    this.setState({
      currentFiles: files,
      isUploading: true,
    });

    const formData = new FormData();
    formData.append("path", this.getRecordPath());

    files.forEach((file) => {
      formData.append("file", file, file.name);
    });

    const xhr = new XMLHttpRequest();
    xhr.open("POST", getApiUrl("/newattachment"));
    xhr.onload = () => {
      this.onUploadComplete(JSON.parse(xhr.responseText));
    };
    xhr.upload.onprogress = (event) => {
      this.onUploadProgress(event);
    };
    xhr.send(formData);
  }

  render() {
    const nai = this.state.newAttachmentInfo;

    if (!nai) {
      return null;
    }

    return (
      <div>
        <h2>{trans("ADD_ATTACHMENT_TO").replace("%s", nai.label)}</h2>
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
          onChange={this.onFileSelected.bind(this)}
        />
        <div className="actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={this.uploadFile.bind(this)}
          >
            {trans("UPLOAD")}
          </button>
        </div>
      </div>
    );
  }
}

export default AddAttachmentPage;
