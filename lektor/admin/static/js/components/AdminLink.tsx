import React, { memo, ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { PageName } from "../context/page-context";
import { RecordPathDetails, useRecord } from "../context/record-context";
import { adminPath } from "./use-go-to-admin-page";

function AdminLink({
  page,
  path,
  alt,
  children,
  ...otherProps
}: RecordPathDetails & {
  page: PageName;
  children: ReactNode;
  onClick?: React.MouseEventHandler<HTMLAnchorElement>;
  ref?: React.MutableRefObject<HTMLAnchorElement | null>;
  title?: string;
}): JSX.Element {
  const current = useRecord();
  const recordMatches = path === current.path && alt === current.alt;

  return (
    <NavLink
      to={adminPath(page, path, alt)}
      activeClassName="active"
      isActive={(match) => recordMatches && match != null}
      {...otherProps}
    >
      {children}
    </NavLink>
  );
}

export default memo(AdminLink);
