import React, { memo } from "react";
import {
  getUrlRecordPath,
  RecordPathDetails,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { RecordInfo } from "../components/types";
import { trans } from "../i18n";

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
            const urlPath = getUrlRecordPath(atch.path, record.alt);
            return (
              <li key={atch.id}>
                <Link to={`${urlPath}/edit`}>
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
