import React, { Component, createRef, RefObject } from "react";
import { RecordProps } from "../components/RecordComponent";
import { getApiUrl } from "../utils";
import { loadData } from "../fetch";
import { trans, trans_format } from "../i18n";
import { showErrorDialog } from "../error-dialog";
import { dispatch } from "../events";

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

type Props = Pick<RecordProps, "record">;

class AddAttachmentPage extends Component<Props, State> {
  fileInput: RefObject<HTMLInputElement>;

  constructor(props: Props) {
    super(props);
    this.state = {
      newAttachmentInfo: null,
      currentFiles: [],
      isUploading: false,
      currentProgress: 0,
    };
    this.fileInput = createRef();
    this.onFileSelected = this.onFileSelected.bind(this);
  }

  componentDidMount() {
    this.syncDialog();
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.record.path !== this.props.record.path) {
      this.syncDialog();
    }
  }

  syncDialog() {
    loadData("/newattachment", { path: this.props.record.path }).then(
      (newAttachmentInfo: NewAttachmentInfo) => {
        this.setState({ newAttachmentInfo });
      },
      showErrorDialog
    );
  }

  onFileSelected({ target }: { target: HTMLInputElement }) {
    if (this.state.isUploading || !target.files) {
      return;
    }

    const files = Array.prototype.slice.call(target.files, 0);
    this.setState({ currentFiles: files, isUploading: true });

    const formData = new FormData();
    formData.append("path", this.props.record.path ?? "");
    files.forEach((file) => {
      formData.append("file", file, file.name);
    });

    const xhr = new XMLHttpRequest();
    xhr.open("POST", getApiUrl("/newattachment"));
    xhr.onprogress = (event) => {
      const newProgress = Math.round((event.loaded * 100) / event.total);
      if (newProgress !== this.state.currentProgress) {
        this.setState({ currentProgress: newProgress });
      }
    };
    xhr.onload = () => {
      this.setState({ isUploading: false, currentProgress: 100 }, () => {
        dispatch("lektor-attachments-changed", this.props.record.path);
      });
    };
    xhr.send(formData);
  }

  render() {
    const { newAttachmentInfo, currentFiles, currentProgress } = this.state;

    if (!newAttachmentInfo) {
      return null;
    }

    return (
      <div>
        <h2>{trans_format("ADD_ATTACHMENT_TO", newAttachmentInfo.label)}</h2>
        <p>{trans("ADD_ATTACHMENT_NOTE")}</p>
        <ul>
          {currentFiles.map((file) => (
            <li key={file.name}>
              {file.name} ({file.type})
            </li>
          ))}
        </ul>
        <p>
          {trans("PROGRESS")}: {currentProgress}%
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
            onClick={() => this.fileInput.current?.click()}
          >
            {trans("UPLOAD")}
          </button>
        </div>
      </div>
    );
  }
}

export default AddAttachmentPage;
