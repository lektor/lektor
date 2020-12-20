import React from "react";
import { WidgetProps } from "./types";
import { trans } from "../i18n";
import InputWidgetBase from "./InputWidgetBase";

function postprocessFloat(value: string) {
  return value.trim();
}

function validateFloat(value: string) {
  if (value && !value.match(/^[+,-]?\d+[.]\d+$/)) {
    return trans("ERROR_INVALID_NUMBER");
  }
  return null;
}

export function FloatInputWidget(props: WidgetProps) {
  return (
    <InputWidgetBase
      inputType="text"
      inputAddon="0.0"
      postprocessValue={postprocessFloat}
      validate={validateFloat}
      {...props}
    />
  );
}
