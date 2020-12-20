import React from "react";
import { WidgetProps } from "./types";
import InputWidgetBase from "./InputWidgetBase";

function postprocessSlug(value: string) {
  return value.replace(/\s+/g, "-");
}

export function SlugInputWidget(props: WidgetProps) {
  return (
    <InputWidgetBase
      inputType="text"
      inputAddon={<i className="fa fa-link" />}
      postprocessValue={postprocessSlug}
      {...props}
    />
  );
}
