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

const inputAddon = <i className="fa fa-external-link" />;

export function UrlInputWidget(props: WidgetProps): JSX.Element {
  return (
    <InputWidgetBase
      inputType="text"
      inputAddon={inputAddon}
      validate={validateUrl}
      {...props}
    />
  );
}
