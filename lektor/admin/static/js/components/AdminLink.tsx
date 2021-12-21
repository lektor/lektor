import React, { memo, ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useRecordAlt } from "./RecordComponent";
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
  const activeAlt = useRecordAlt();

  return (
    <NavLink
      to={adminPath(page, path, alt)}
      activeClassName="active"
      isActive={(match) => !!(match && alt === activeAlt)}
    >
      {children}
    </NavLink>
  );
}

export default memo(AdminLink);
