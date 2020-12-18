import React from "react";
import { trans } from "./i18n";

/**
 * Formats a user label appropriately
 */
export function formatUserLabel(inputConfig) {
  const label =
    typeof inputConfig === "string" ? inputConfig : trans(inputConfig);

  if (!label) {
    return <span className="" />;
  }

  const iconData = label.match(/^\[\[\s*(.*?)\s*(;\s*(.*?))?\s*\]\]$/);
  if (iconData) {
    let className = "fa fa-" + iconData[1];
    if ((iconData[3] || "").match(/90|180|270/)) {
      className += " fa-rotate-" + iconData[3];
    }
    return <i className={className} />;
  }

  return <span>{label}</span>;
}
