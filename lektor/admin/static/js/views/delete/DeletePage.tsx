import React, { useCallback, useEffect, useState } from "react";
import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../../components/RecordComponent";
import { getParentFsPath } from "../../utils";
import { loadData } from "../../fetch";
import { showErrorDialog } from "../../error-dialog";
import { RecordInfo } from "../../components/types";
import DeletableAttachments from "./DeletableAttachments";
import DeletableChildPages from "./DeletableChildPages";
import DeletableAlternatives from "./DeletableAlternatives";
import DeletePageActions from "./DeletePageActions";
import DeleteAllAltsChoice from "./DeleteAllAltsChoice";
import DeletePageHeader from "./DeletePageHeader";
import { dispatch } from "../../events";
import { useHistory } from "react-router";

type Props = Pick<RecordProps, "record" | "history">;

function DeletePage({ record }: Props) {
  const [recordInfo, setRecordInfo] = useState<RecordInfo | null>(null);
  const [deleteMasterRecord, setDeleteMasterRecord] = useState(true);

  const history = useHistory();
  const { alt, path } = record;

  useEffect(() => {
    let ignore = false;

    loadData("/recordinfo", { path }).then((resp: RecordInfo) => {
      if (!ignore) {
        setRecordInfo(resp);
      }
    }, showErrorDialog);

    return () => {
      ignore = true;
    };
  }, [path]);

  useEffect(() => {
    setDeleteMasterRecord(alt === "_primary");
  }, [alt]);

  const deleteRecord = useCallback(() => {
    const parent = getParentFsPath(path || "");
    const targetPath = parent === null ? "root" : getUrlRecordPath(parent, alt);

    loadData(
      "/deleterecord",
      { path, alt, delete_master: deleteMasterRecord ? "1" : "0" },
      { method: "POST" }
    ).then(() => {
      if (recordInfo?.is_attachment) {
        dispatch("lektor-attachments-changed", parent ?? "");
      }
      history.push(pathToAdminPage("edit", targetPath));
    }, showErrorDialog);
  }, [alt, path, deleteMasterRecord, history, recordInfo]);

  const cancelDelete = useCallback(() => {
    const urlPath = getUrlRecordPath(record.path, record.alt);
    history.push(pathToAdminPage("edit", urlPath));
  }, [history, record]);

  if (!recordInfo || !recordInfo.can_be_deleted) {
    return null;
  }

  const hasAlts = recordInfo.alts.filter((a) => a.exists).length > 1;

  return (
    <div>
      <DeletePageHeader recordInfo={recordInfo} currentAlt={alt} />
      {hasAlts && alt === "_primary" && (
        <DeleteAllAltsChoice
          deleteMasterRecord={deleteMasterRecord}
          setDeleteMasterRecord={setDeleteMasterRecord}
          isAttachment={recordInfo.is_attachment}
        />
      )}
      {deleteMasterRecord && (
        <>
          {hasAlts && alt === "_primary" && (
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
        deleteRecord={deleteRecord}
        cancelDelete={cancelDelete}
      />
    </div>
  );
}

export default DeletePage;
