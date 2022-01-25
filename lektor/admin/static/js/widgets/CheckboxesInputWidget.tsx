import React from "react";
import { trans_obj } from "../i18n";
import { MultiWidgetType, WidgetProps } from "./types";

const checkboxIsActive = (field: string, value: string[] | null) =>
  value !== null && value.includes(field);

const flipSetValue = (set: string[], value: string, isActive: boolean) => {
  if (isActive) {
    return set.includes(value) ? set : [...set, value];
  } else {
    return set.filter((v) => v !== value);
  }
};

const deserialize = (value?: string): string[] | null => {
  if (!value) {
    return null;
  }
  let rv = value.split(",").map((x) => x.trim());
  if (rv.length === 1 && rv[0] === "") {
    rv = [];
  }
  return rv;
};

export function CheckboxesInputWidget({
  disabled,
  type,
  onChange,
  value,
  placeholder,
}: WidgetProps<string, MultiWidgetType>): JSX.Element {
  const deserializedValue = deserialize(value);
  const deserializedPlaceholder = deserialize(placeholder);

  return (
    <div className="checkboxes-widget">
      {type.choices?.map(([key, description]) => (
        <div className="form-check" key={key}>
          <label className="form-check-label">
            <input
              className="form-check-input"
              type="checkbox"
              disabled={disabled}
              checked={checkboxIsActive(
                key,
                deserializedValue ?? deserializedPlaceholder
              )}
              onChange={(ev) => {
                const newValue = flipSetValue(
                  deserializedValue || [],
                  key,
                  ev.target.checked
                );
                onChange(newValue.join(", "));
              }}
            />
            {trans_obj(description)}
          </label>
        </div>
      ))}
    </div>
  );
}
