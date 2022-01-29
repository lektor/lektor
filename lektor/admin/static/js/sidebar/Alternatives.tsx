import React, { memo, useContext } from "react";
import { Alternative } from "../components/types";
import { trans, trans_obj } from "../i18n";
import AdminLink from "../components/AdminLink";
import { PageContext } from "../context/page-context";
import { useRecordPath } from "../context/record-context";

function Alternatives({ alts }: { alts: Alternative[] }) {
  const page = useContext(PageContext);
  const path = useRecordPath();

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
        <AdminLink page={page as "edit"} path={path} alt={item.alt}>
          {title}
        </AdminLink>
      </li>
    );
  });

  return (
    <>
      <h3>{trans("ALTS")}</h3>
      <ul className="nav">{items}</ul>
    </>
  );
}

export default memo(Alternatives);
