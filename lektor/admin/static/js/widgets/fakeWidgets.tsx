import { WidgetProps } from "./mixins";
import React from "react";
import { trans } from "../i18n";

export function LineWidget() {
  return <hr />;
}
LineWidget.isFakeWidget = true;

export function SpacingWidget() {
  return <div className="spacing" />;
}
SpacingWidget.isFakeWidget = true;

export function InfoWidget(props: WidgetProps) {
  const label = trans(props.field.label_i18n);
  return (
    <div className="info">
      <p>
        {label ? <strong>{label + ": "}</strong> : null}
        {trans(props.field.description_i18n)}
      </p>
    </div>
  );
}
InfoWidget.isFakeWidget = true;

export function HeadingWidget(props: WidgetProps) {
  return <h3>{trans(props.type.heading_i18n)}</h3>;
}
HeadingWidget.isFakeWidget = true;
