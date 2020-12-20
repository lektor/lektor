import React from "react";
import { WidgetProps } from "./types";
import { trans } from "../i18n";
import InputWidgetBase from "./InputWidgetBase";

function postprocessInteger(value: string) {
  return value.trim();
}

function validateInteger(value: string) {
  if (value && !value.match(/^-?\d+$/)) {
    return trans("ERROR_INVALID_NUMBER");
  }
  return null;
}

export function IntegerInputWidget(props: WidgetProps) {
  return (
    <InputWidgetBase
      inputType="text"
      inputAddon="0"
      postprocessValue={postprocessInteger}
      validate={validateInteger}
      {...props}
    />
  );
}
