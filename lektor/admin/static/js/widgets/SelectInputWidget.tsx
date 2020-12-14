import React from "react";
import { trans } from "../i18n";
import { getInputClass, WidgetProps } from "./mixins";

export function SelectInputWidget(props: WidgetProps) {
  const { type, value, placeholder, onChange, disabled } = props;

  const choices = type.choices.map((item) => (
    <option key={item[0]} value={item[0]}>
      {trans(item[1])}
    </option>
  ));

  return (
    <div className="form-group">
      <div>
        <select
          className={getInputClass(type)}
          value={value || placeholder || ""}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        >
          <option key="" value="">
            ----
          </option>
          {choices}
        </select>
      </div>
    </div>
  );
}
