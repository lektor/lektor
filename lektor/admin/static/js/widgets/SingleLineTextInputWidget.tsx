import React from "react";
import { WidgetProps } from "./types";
import InputWidgetBase from "./InputWidgetBase";

export function SingleLineTextInputWidget(props: WidgetProps): JSX.Element {
  return (
    <InputWidgetBase
      inputType="text"
      inputAddon={<i className="fa fa-paragraph" />}
      {...props}
    />
  );
}
