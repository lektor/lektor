import React from "react";
import { trans } from "../../i18n";
import { RecordInfo } from "../../components/types";

export function DeletableAttachments({
  recordInfo,
}: {
  recordInfo: RecordInfo;
}): JSX.Element {
  return (
    <div>
      <h4>{trans("ATTACHMENTS_TO_BE_DELETED")}</h4>
      <ul>
        {recordInfo.attachments.map((atch) => (
          <li key={atch.id}>
            {atch.id} ({atch.type})
          </li>
        ))}
      </ul>
    </div>
  );
}
