import React from "react";
import { trans, trans_fallback, trans_format, trans_obj } from "../../i18n";
import { RecordInfo } from "../../components/types";

export function DeletePageHeader({
  recordInfo,
  currentAlt,
}: {
  recordInfo: RecordInfo;
  currentAlt: string;
}): JSX.Element {
  const isPrimary = currentAlt === "_primary";
  const altInfo = recordInfo.alts.find((a) => a.alt === currentAlt);

  let label = trans_fallback(recordInfo.label_i18n, recordInfo.id);
  if (!isPrimary && altInfo) {
    label += ` (${trans_obj(altInfo.name_i18n)})`;
  }

  return (
    <>
      <h2>{trans_format("DELETE_RECORD", label)}</h2>
      {recordInfo.is_attachment ? (
        <p>
          {isPrimary
            ? trans("DELETE_ATTACHMENT_PROMPT")
            : trans("DELETE_ATTACHMENT_ALT_PROMPT")}{" "}
        </p>
      ) : (
        <p>
          {isPrimary
            ? trans("DELETE_PAGE_PROMPT")
            : trans("DELETE_PAGE_ALT_PROMPT")}{" "}
          {recordInfo.children.length > 0 && isPrimary
            ? trans("DELETE_PAGE_CHILDREN_WARNING")
            : null}
        </p>
      )}
    </>
  );
}
