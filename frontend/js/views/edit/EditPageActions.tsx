import React, { useCallback } from "react";
import { useRecord } from "../../context/record-context";
import { useGoToAdminPage } from "../../components/use-go-to-admin-page";
import { trans } from "../../i18n";
import { RawRecordInfo } from "./EditPage";

export function EditPageActions({
  recordInfo,
  hasPendingChanges,
}: {
  recordInfo: RawRecordInfo;
  hasPendingChanges: boolean;
}): React.JSX.Element {
  const { path, alt } = useRecord();
  const goToAdminPage = useGoToAdminPage();

  const deleteRecord = useCallback(() => {
    goToAdminPage("delete", path, alt);
  }, [alt, goToAdminPage, path]);

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
