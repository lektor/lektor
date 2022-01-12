import React, { memo, ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { PageName, RecordPathDetails, useRecord } from "./RecordComponent";
import { adminPath } from "./use-go-to-admin-page";

function AdminLink({
  page,
  path,
  alt,
  children,
}: RecordPathDetails & {
  page: PageName;
  children: ReactNode;
}): JSX.Element {
  const current = useRecord();
  const recordMatches = path === current.path && alt === current.alt;

  return (
    <NavLink
      to={adminPath(page, path, alt)}
      activeClassName="active"
      isActive={(match) => !!(recordMatches && match)}
    >
      {children}
    </NavLink>
  );
}

export default memo(AdminLink);
