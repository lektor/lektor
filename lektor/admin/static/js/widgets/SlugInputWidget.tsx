import React from "react";
import { WidgetProps } from "./types";
import InputWidgetBase from "./InputWidgetBase";

function postprocessSlug(value: string) {
  return value.replace(/\s+/g, "-");
}

const inputAddon = <i className="fa fa-link" />;

export function SlugInputWidget(props: WidgetProps): JSX.Element {
  return (
    <InputWidgetBase
      inputType="text"
      inputAddon={inputAddon}
      postprocessValue={postprocessSlug}
      {...props}
    />
  );
}
