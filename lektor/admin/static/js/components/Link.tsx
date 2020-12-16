import React, { ReactNode } from "react";
import { NavLink } from "react-router-dom";

export default function LektorLink(props: { to: string; children: ReactNode }) {
  let path = props.to;
  if (path.substr(0, 1) !== "/") {
    path = `${$LEKTOR_CONFIG.admin_root}/${path}`;
  }
  return (
    <NavLink to={path} activeClassName="active">
      {props.children}
    </NavLink>
  );
}
