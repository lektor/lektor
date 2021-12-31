import React, { memo, ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { adminPath } from "./use-go-to-admin-page";

function AdminLink({
  page,
  path,
  alt,
  children,
}: {
  page: "edit" | "preview" | "delete" | "add-child" | "upload";
  path: string;
  alt: string;
  children: ReactNode;
}): JSX.Element {
  return (
    <NavLink to={adminPath(page, path, alt)} activeClassName="active">
      {children}
    </NavLink>
  );
}

export default memo(AdminLink);
