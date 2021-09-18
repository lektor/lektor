import React from "react";
import { trans, trans_obj } from "../../i18n";
import { RecordInfo } from "../../components/types";

export function DeletableAlternatives({
  recordInfo,
}: {
  recordInfo: RecordInfo;
}): JSX.Element {
  return (
    <div>
      <h4>{trans("ALTS_TO_BE_DELETED")}</h4>
      <ul>
        {recordInfo.alts
          .filter((i) => i.exists)
          .map((item) => {
            let title = trans_obj(item.name_i18n);
            if (item.is_primary) {
              title += " (" + trans("PRIMARY_ALT") + ")";
            } else if (item.primary_overlay) {
              title += " (" + trans("PRIMARY_OVERLAY") + ")";
            }
            return <li key={item.alt}>{title}</li>;
          })}
      </ul>
    </div>
  );
}
