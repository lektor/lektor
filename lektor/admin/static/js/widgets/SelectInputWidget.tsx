import React from "react";
import { trans_obj } from "../i18n";
import { getInputClass, MultiWidgetType, WidgetProps } from "./types";

export function SelectInputWidget(props: WidgetProps<string, MultiWidgetType>) {
  const { type, value, placeholder, onChange, disabled } = props;

  const choices = type.choices?.map((item) => (
    <option key={item[0]} value={item[0]}>
      {trans_obj(item[1])}
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
