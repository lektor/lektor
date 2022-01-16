import React, { memo } from "react";
import AdminLink from "../components/AdminLink";
import { useRecordAlt } from "../context/record-context";
import { RecordInfo } from "../components/types";
import { trans } from "../i18n";

function AttachmentActions({ recordInfo }: { recordInfo: RecordInfo }) {
  const alt = useRecordAlt();
  const attachments = recordInfo.attachments;
  return (
    <>
      <h3>{trans("ATTACHMENTS")}</h3>
      <ul className="nav">
        {attachments.length > 0 ? (
          attachments.map((atch) => {
            return (
              <li key={atch.id}>
                <AdminLink page="edit" path={atch.path} alt={alt}>
                  {atch.id} ({atch.type})
                </AdminLink>
              </li>
            );
          })
        ) : (
          <li key="_missing">
            <em>{trans("NO_ATTACHMENTS")}</em>
          </li>
        )}
      </ul>
    </>
  );
}

export default memo(AttachmentActions);
