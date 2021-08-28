import React, { ReactNode } from "react";
import { IntegerInputWidget } from "./widgets/IntegerInputWidget";
import { MultiLineTextInputWidget } from "./widgets/MultiLineTextInputWidget";
import { BooleanInputWidget } from "./widgets/BooleanInputWidget";
import { DateInputWidget } from "./widgets/DateInputWidget";
import { FloatInputWidget } from "./widgets/FloatInputWidget";
import { UrlInputWidget } from "./widgets/UrlInputWidget";
import { SlugInputWidget } from "./widgets/SlugInputWidget";
import { SingleLineTextInputWidget } from "./widgets/SingleLineTextInputWidget";
import { CheckboxesInputWidget } from "./widgets/CheckboxesInputWidget";
import { SelectInputWidget } from "./widgets/SelectInputWidget";
import { FlowWidget } from "./widgets/FlowWidget";
import {
  LineWidget,
  SpacingWidget,
  InfoWidget,
  HeadingWidget,
} from "./widgets/fakeWidgets";
import {
  Field,
  WidgetComponent,
  WidgetProps,
  WidgetType,
} from "./widgets/types";
import { trans_obj } from "./i18n";

const widgetComponents = {
  "singleline-text": SingleLineTextInputWidget,
  "multiline-text": MultiLineTextInputWidget,
  datepicker: DateInputWidget,
  integer: IntegerInputWidget,
  float: FloatInputWidget,
  checkbox: BooleanInputWidget,
  url: UrlInputWidget,
  slug: SlugInputWidget,
  flow: FlowWidget,
  checkboxes: CheckboxesInputWidget,
  select: SelectInputWidget,
  "f-line": LineWidget,
  "f-spacing": SpacingWidget,
  "f-info": InfoWidget,
  "f-heading": HeadingWidget,
};

/**
 * A fallback widget to render for fields missing a component.
 */
function FallbackWidget(props: WidgetProps) {
  return (
    <div>
      <em>
        {`Widget "${props.type.widget}" not implemented`}
        {` (used by type "${props.type.name}")`}
      </em>
    </div>
  );
}

/**
 * An input widget wrapped in a <div> with description and label.
 */
export const FieldBox = React.memo(function FieldBox(props: {
  field: Field;
  value: string;
  placeholder: string | null;
  disabled?: boolean;
  setFieldValue: (field: Field, value: string, uiChange?: boolean) => void;
}) {
  const { field, value, placeholder, disabled } = props;
  const onChange = (value: string, uiChange?: boolean) =>
    props.setFieldValue(field, value, uiChange);
  const className = `col-md-${getFieldColumns(field)}`;

  const Widget = getWidgetComponentWithFallback(field.type);
  if (Widget.isFakeWidget) {
    return (
      <div className={className} key={field.name}>
        <Widget key={field.name} field={field} />
      </div>
    );
  }

  const description = field.description_i18n ? (
    <div className="help-text">{trans_obj(field.description_i18n)}</div>
  ) : null;

  return (
    <div className={className} key={field.name}>
      <dl className="field">
        {!field.hide_label ? <dt>{trans_obj(field.label_i18n)}</dt> : null}
        <dd>
          {description}
          <Widget
            value={value}
            onChange={onChange}
            type={field.type}
            placeholder={placeholder ?? undefined}
            disabled={disabled}
          />
        </dd>
      </dl>
    </div>
  );
});

export function getWidgetComponent(type: WidgetType): WidgetComponent | null {
  // @ts-expect-error This is hard to type and not typed yet.
  return widgetComponents[type.widget] || null;
}

export function getWidgetComponentWithFallback(
  type: WidgetType
): WidgetComponent {
  // @ts-expect-error This is hard to type and not typed yet.
  return widgetComponents[type.widget] || FallbackWidget;
}

/**
 * Get the width of a field in columns.
 */
export function getFieldColumns(field: { type: Pick<WidgetType, "width"> }) {
  const widthSpec = (field.type.width || "1/1").split("/");
  const fraction = (12 * +widthSpec[0]) / +widthSpec[1];
  return Number.isNaN(fraction)
    ? 12
    : Math.min(12, Math.max(2, parseInt(`${fraction}`)));
}

/**
 * Process fields into rows.
 */
function processFields(fields: Field[]) {
  const rows = [];
  let currentColumns = 0;
  let row: Field[] = [];

  fields.forEach((field) => {
    const columns = getFieldColumns(field);
    if (columns + currentColumns > 12) {
      rows.push(row);
      currentColumns = 0;
      row = [];
    }
    row.push(field);
    currentColumns += columns;
  });

  if (row.length > 0) {
    rows.push(row);
  }
  return rows;
}

/**
 * Split the fields into normal and system fields.
 */
export function splitFields(fields: Field[]) {
  const normalFields: Field[] = [];
  const systemFields: Field[] = [];

  fields.forEach((field) => {
    if (field.name.substr(0, 1) === "_") {
      systemFields.push(field);
    } else {
      normalFields.push(field);
    }
  });

  return [normalFields, systemFields];
}

/**
 * Render field rows using a render function.
 */
export function FieldRows({
  fields,
  renderFunc,
}: {
  fields: Field[];
  renderFunc: (field: Field, index: number) => ReactNode;
}) {
  return (
    <>
      {processFields(fields).map((row, idx) => (
        <div className="row field-row" key={"normal-" + idx}>
          {row.map(renderFunc)}
        </div>
      ))}
    </>
  );
}
