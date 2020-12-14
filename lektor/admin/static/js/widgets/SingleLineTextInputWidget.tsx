import React from "react";
import { WidgetProps } from "./mixins";
import InputWidgetBase from "./InputWidgetBase";

export function SingleLineTextInputWidget(props: WidgetProps) {
  return (
    <InputWidgetBase
      inputType="text"
      inputAddon={<i className="fa fa-paragraph" />}
      {...props}
    />
  );
}
