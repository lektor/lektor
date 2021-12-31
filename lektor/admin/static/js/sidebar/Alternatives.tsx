import React, { memo } from "react";
import { RecordProps } from "../components/RecordComponent";
import Link from "../components/Link";
import { Alternative } from "../components/types";
import { trans, trans_obj } from "../i18n";
import { adminPath } from "../components/use-go-to-admin-page";

type Props = RecordProps & { alts: Alternative[] };

function Alternatives({ alts, page, record }: Props) {
  if (alts.length < 2) {
    return null;
  }

  const items = alts.map((item) => {
    let title = trans_obj(item.name_i18n);
    if (item.is_primary) {
      title += ` (${trans("PRIMARY_ALT")})`;
    } else if (item.primary_overlay) {
      title += ` (${trans("PRIMARY_OVERLAY")})`;
    }
    const className = item.exists ? "alt" : "alt alt-missing";

    return (
      <li key={item.alt} className={className}>
        <Link to={adminPath(page, record.path, item.alt)}>{title}</Link>
      </li>
    );
  });

  return (
    <div className="section">
      <h3>{trans("ALTS")}</h3>
      <ul className="nav">{items}</ul>
    </div>
  );
}

export default memo(Alternatives);
