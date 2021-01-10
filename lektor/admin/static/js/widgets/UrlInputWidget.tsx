import React from "react";
import { WidgetProps } from "./types";
import InputWidgetBase from "./InputWidgetBase";
import { isValidUrl } from "../utils";
import { trans } from "../i18n";

function validateUrl(value: string) {
  if (value && !isValidUrl(value)) {
    return trans("ERROR_INVALID_URL");
  }
  return null;
}

export function UrlInputWidget(props: WidgetProps) {
  return (
    <InputWidgetBase
      inputType="text"
      inputAddon={<i className="fa fa-external-link" />}
      validate={validateUrl}
      {...props}
    />
  );
}
