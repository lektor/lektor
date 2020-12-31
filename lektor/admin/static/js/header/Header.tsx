import React from "react";
import { RecordProps } from "../components/RecordComponent";

import BreadCrumbs from "./BreadCrumbs";

export default function Header({
  sidebarIsActive,
  toggleSidebar,
  ...recordProps
}: {
  sidebarIsActive: boolean;
  toggleSidebar: () => void;
} & RecordProps) {
  const buttonClass = sidebarIsActive
    ? "navbar-toggle active"
    : "navbar-toggle";

  return (
    <header>
      <BreadCrumbs {...recordProps}>
        <button type="button" className={buttonClass} onClick={toggleSidebar}>
          <span className="sr-only">Toggle navigation</span>
          <span className="icon-list" />
          <span className="icon-list" />
          <span className="icon-list" />
        </button>
      </BreadCrumbs>
    </header>
  );
}
