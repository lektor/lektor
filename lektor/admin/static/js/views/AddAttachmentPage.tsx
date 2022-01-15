import React, {
  ChangeEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { RecordProps } from "../components/RecordComponent";
import { apiUrl, get } from "../fetch";
import { trans, trans_format } from "../i18n";
import { showErrorDialog } from "../error-dialog";
import { dispatch } from "../events";

type NewAttachmentInfo = {
  label: string;
  can_upload: boolean;
};

function AddAttachmentPage({
  record,
}: Pick<RecordProps, "record">): JSX.Element | null {
  const [newAttachmentInfo, setNewAttachmentInfo] =
    useState<NewAttachmentInfo | null>(null);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [currentFiles, setCurrentFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [currentProgress, setCurrentProgress] = useState(0);
  const path = record.path;

  useEffect(() => {
    let ignore = false;

    get("/newattachment", { path }).then((resp) => {
      if (!ignore) {
        setNewAttachmentInfo(resp);
      }
    }, showErrorDialog);
    return () => {
      ignore = true;
    };
  }, [path]);

  const onFileSelected = useCallback(
    ({ target }: ChangeEvent<HTMLInputElement>) => {
      if (isUploading || !target.files) {
        return;
      }

      const files = Array.prototype.slice.call(target.files, 0);
      setCurrentFiles(files);
      setIsUploading(true);

      const formData = new FormData();
      formData.append("path", path);
      files.forEach((file) => {
        formData.append("file", file, file.name);
      });

      const xhr = new XMLHttpRequest();
      xhr.open("POST", apiUrl("/newattachment"));
      xhr.onprogress = (event) => {
        setCurrentProgress(Math.round((event.loaded * 100) / event.total));
      };
      xhr.onload = () => {
        setIsUploading(false);
        setCurrentProgress(100);
        dispatch("lektor-attachments-changed", path);
      };
      xhr.send(formData);
    },
    [path, isUploading]
  );

  if (!newAttachmentInfo) {
    return null;
  }

  return (
    <>
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
        ref={fileInput}
        multiple
        style={{ display: "none" }}
        onChange={onFileSelected}
      />
      <div className="actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => fileInput.current?.click()}
        >
          {trans("UPLOAD")}
        </button>
      </div>
    </>
  );
}

export default AddAttachmentPage;
