import React from "react";
import { trans } from "../../i18n";

export function DeleteAllAltsChoice({
  deleteMasterRecord,
  setDeleteMasterRecord,
  isAttachment,
}: {
  deleteMasterRecord: boolean;
  setDeleteMasterRecord: (v: boolean) => void;
  isAttachment: boolean;
}): JSX.Element {
  return (
    <>
      <p>{trans("DELETE_PRIMARY_ALT_INFO")}</p>
      <ul>
        <li>
          <label>
            <input
              type="radio"
              checked={deleteMasterRecord}
              onChange={() => setDeleteMasterRecord(true)}
            />{" "}
            {trans(
              isAttachment
                ? "DELETE_ALL_ATTACHMENT_ALTS"
                : "DELETE_ALL_PAGE_ALTS"
            )}
          </label>
        </li>
        <li>
          <label>
            <input
              type="radio"
              checked={!deleteMasterRecord}
              onChange={() => setDeleteMasterRecord(false)}
            />{" "}
            {trans(
              isAttachment
                ? "DELETE_ONLY_PRIMARY_ATTACHMENT_ALT"
                : "DELETE_ONLY_PRIMARY_PAGE_ALT"
            )}
          </label>
        </li>
      </ul>
    </>
  );
}
