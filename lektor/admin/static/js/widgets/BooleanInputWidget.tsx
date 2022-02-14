import React from "react";
import { WidgetProps } from "./types";
import { trans_obj } from "../i18n";

const isTrue = (value?: string) =>
  value === "true" || value === "yes" || value === "1";

export function BooleanInputWidget({
  type,
  value,
  disabled,
  placeholder,
  onChange,
}: WidgetProps): JSX.Element {
  return (
    <div className="form-check">
      <label className="form-check-label">
        <input
          type="checkbox"
          className="form-check-input"
          disabled={disabled}
          ref={(checkbox) => {
            if (checkbox) {
              if (!value && placeholder) {
                checkbox.indeterminate = true;
                checkbox.checked = isTrue(placeholder);
              } else {
                checkbox.indeterminate = false;
              }
            }
          }}
          checked={isTrue(value)}
          onChange={(ev) => {
            onChange(ev.target.checked ? "yes" : "no");
          }}
        />
        {type.checkbox_label_i18n ? trans_obj(type.checkbox_label_i18n) : null}
      </label>
    </div>
  );
}
