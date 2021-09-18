import React from "react";
import { trans } from "../../i18n";

export function DeletePageActions({
  deleteRecord,
  cancelDelete,
}: {
  deleteRecord: () => void;
  cancelDelete: () => void;
}): JSX.Element {
  return (
    <div className="actions">
      <button type="button" className="btn btn-primary" onClick={deleteRecord}>
        {trans("YES_DELETE")}
      </button>
      <button
        type="button"
        className="btn btn-secondary border"
        onClick={cancelDelete}
      >
        {trans("NO_CANCEL")}
      </button>
    </div>
  );
}
