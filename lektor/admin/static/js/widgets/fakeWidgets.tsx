import { Field } from "./mixins";
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

export function InfoWidget(props: { field: Field }) {
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

export function HeadingWidget(props: { field: Field }) {
  return <h3>{trans(props.field.type.heading_i18n ?? {})}</h3>;
}
HeadingWidget.isFakeWidget = true;
