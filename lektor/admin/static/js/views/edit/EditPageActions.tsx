import React, { useCallback } from "react";
import { useHistory } from "react-router-dom";
import {
  getUrlRecordPathWithAlt,
  pathToAdminPage,
  RecordPathDetails,
} from "../../components/RecordComponent";
import { trans } from "../../i18n";
import { RawRecordInfo } from "./EditPage";

export function EditPageActions({
  recordInfo,
  hasPendingChanges,
  record,
}: {
  recordInfo: RawRecordInfo;
  hasPendingChanges: boolean;
  record: RecordPathDetails;
}): JSX.Element {
  const history = useHistory();

  const deleteRecord = useCallback(() => {
    history.push(
      pathToAdminPage(
        "delete",
        getUrlRecordPathWithAlt(record.path, record.alt)
      )
    );
  }, [record, history]);

  return (
    <div className="actions">
      <button
        type="submit"
        disabled={!hasPendingChanges}
        className="btn btn-primary"
      >
        {trans("SAVE_CHANGES")}
      </button>
      {recordInfo.can_be_deleted ? (
        <button
          type="button"
          className="btn btn-secondary border"
          onClick={deleteRecord}
        >
          {trans("DELETE")}
        </button>
      ) : null}
    </div>
  );
}
