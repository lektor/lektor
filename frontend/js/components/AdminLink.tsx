import React, { memo, ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { PageName } from "../context/page-context";
import { RecordPathDetails, useRecord } from "../context/record-context";
import { adminPath } from "./use-go-to-admin-page";

export type AdminLinkProps = RecordPathDetails & {
  page: PageName;
  children: ReactNode;
  onClick?: React.MouseEventHandler<HTMLAnchorElement>;
  title?: string;
};

/**
 * Link to an admin page.
 */
function AdminLink({
  page,
  path,
  alt,
  children,
  ...otherProps
}: AdminLinkProps): JSX.Element {
  const current = useRecord();
  const recordMatches = path === current.path && alt === current.alt;

  return (
    <NavLink
      to={adminPath(page, path, alt)}
      className={({ isActive }) =>
        isActive && recordMatches ? "active" : undefined
      }
      {...otherProps}
    >
      {children}
    </NavLink>
  );
}

export default memo(AdminLink);
