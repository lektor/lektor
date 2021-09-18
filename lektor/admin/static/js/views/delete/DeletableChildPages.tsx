import React from "react";
import { trans, trans_obj } from "../../i18n";
import { RecordInfo } from "../../components/types";

export function DeletableChildPages({
  recordInfo,
}: {
  recordInfo: RecordInfo;
}): JSX.Element {
  return (
    <div>
      <h4>{trans("CHILD_PAGES_TO_BE_DELETED")}</h4>
      <ul>
        {recordInfo.children.map((child) => (
          <li key={child.id}>{trans_obj(child.label_i18n)}</li>
        ))}
      </ul>
    </div>
  );
}
