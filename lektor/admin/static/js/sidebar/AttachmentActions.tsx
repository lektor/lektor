import React, { memo } from "react";
import { RecordPathDetails } from "../components/RecordComponent";
import Link from "../components/Link";
import { RecordInfo } from "../components/types";
import { trans } from "../i18n";
import { adminPath } from "../components/use-go-to-admin-page";

function AttachmentActions({
  recordInfo,
  record,
}: {
  record: RecordPathDetails;
  recordInfo: RecordInfo;
}) {
  const attachments = recordInfo.attachments;
  return (
    <div className="section">
      <h3>{trans("ATTACHMENTS")}</h3>
      <ul className="nav record-attachments">
        {attachments.length > 0 ? (
          attachments.map((atch) => {
            return (
              <li key={atch.id}>
                <Link to={adminPath("edit", atch.path, record.alt)}>
                  {atch.id} ({atch.type})
                </Link>
              </li>
            );
          })
        ) : (
          <li key="_missing">
            <em>{trans("NO_ATTACHMENTS")}</em>
          </li>
        )}
      </ul>
    </div>
  );
}

export default memo(AttachmentActions);
