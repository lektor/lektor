import React from "react";
import { trans } from "../i18n";
import { getInputClass, WidgetProps } from "./mixins";

export function SelectInputWidget(props: WidgetProps) {
  const {
    className,
    type,
    value,
    placeholder,
    onChange,
    ...otherProps
  } = props;

  const choices = type.choices.map((item) => (
    <option key={item[0]} value={item[0]}>
      {trans(item[1])}
    </option>
  ));

  return (
    <div className="form-group">
      <div className={className}>
        <select
          className={getInputClass(type)}
          value={value || placeholder || ""}
          onChange={(e) => onChange(e.target.value)}
          {...otherProps}
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
