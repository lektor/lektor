import React from "react";
import { formatUserLabel } from "../../userLabel";
import { getWidgetComponentWithFallback } from "../../widgets";
import { Field } from "../../widgets/types";

/**
 * The input to change the primary field value for the new child page.
 */
export default function PrimaryField({
  primary,
  field,
  setPrimary,
}: {
  primary: string;
  setPrimary: (s: string) => void;
  field: Field;
}): JSX.Element {
  const Widget = getWidgetComponentWithFallback(field.type);
  const value = Widget.deserializeValue
    ? Widget.deserializeValue(primary, field.type)
    : primary;

  return (
    <div className="row field-row">
      <div className="col-md-12">
        <dl className="field">
          <dt>{formatUserLabel(field.label_i18n)}</dt>
          <dd>
            <Widget
              value={value}
              onChange={setPrimary}
              type={field.type}
              field={field}
            />
          </dd>
        </dl>
      </div>
    </div>
  );
}
