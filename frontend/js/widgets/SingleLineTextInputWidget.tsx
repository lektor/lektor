import React from "react";
import { WidgetProps } from "./types";
import InputWidgetBase from "./InputWidgetBase";

const inputAddon = <i className="fa fa-paragraph" />;

export function SingleLineTextInputWidget(
  props: WidgetProps,
): React.JSX.Element {
  return (
    <InputWidgetBase inputType="text" inputAddon={inputAddon} {...props} />
  );
}
