import React, { useEffect, useRef } from "react";
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
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const input = ref.current;
    if (input) {
      input.indeterminate = !value;
    }
  }, [value]);

  return (
    <div className="form-check">
      <label className="form-check-label">
        <input
          type="checkbox"
          className="form-check-input"
          disabled={disabled}
          ref={ref}
          checked={isTrue(value || placeholder)}
          onChange={(ev) => {
            onChange(ev.target.checked ? "yes" : "no");
          }}
        />
        {type.checkbox_label_i18n ? trans_obj(type.checkbox_label_i18n) : null}
      </label>
    </div>
  );
}
