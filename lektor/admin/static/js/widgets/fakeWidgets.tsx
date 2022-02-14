import { Field } from "./types";
import React from "react";
import { trans_obj } from "../i18n";

export function LineWidget(): JSX.Element {
  return <hr />;
}
LineWidget.isFakeWidget = true;

export function SpacingWidget(): JSX.Element {
  return <div className="spacing-widget" />;
}
SpacingWidget.isFakeWidget = true;

export function InfoWidget(props: { field: Field }): JSX.Element {
  const label = trans_obj(props.field.label_i18n);
  return (
    <div className="info-widget">
      <p>
        {label ? <strong>{label + ": "}</strong> : null}
        {trans_obj(props.field.description_i18n)}
      </p>
    </div>
  );
}
InfoWidget.isFakeWidget = true;

export function HeadingWidget(props: { field: Field }): JSX.Element {
  return <h3>{trans_obj(props.field.type.heading_i18n ?? {})}</h3>;
}
HeadingWidget.isFakeWidget = true;
