import React, { KeyboardEvent } from "react";
import { WidgetProps } from "./types";
import { trans, trans_obj } from "../i18n";

const isTrue = (value?: string | null) =>
  value === "true" || value === "yes" || value === "1";

const isDeleteOrBackspace = (event: KeyboardEvent<HTMLInputElement>) => {
  if (event.altKey || event.metaKey || (event.shiftKey && !event.ctrlKey)) {
    // If modifiers other than <ctrl>, <ctrl>-<shift>, or none are used, ignore
    return false;
  }
  return event.key === "Delete" || event.key === "Backspace";
};

export function BooleanInputWidget({
  type,
  value,
  disabled,
  placeholder,
  onChange,
}: WidgetProps<string | null>): React.JSX.Element {
  return (
    <div className="form-check">
      <label className="form-check-label">
        <input
          type="checkbox"
          className={[
            "form-check-input",
            `form-check-input--default-${placeholder ? "true" : "false"}`,
          ].join(" ")}
          disabled={disabled}
          ref={(checkbox) => {
            if (checkbox) {
              // wierdly, `indeterminate` can not be set via HTML attribute
              checkbox.indeterminate = !value;
            }
          }}
          checked={isTrue(value || placeholder)}
          onChange={(ev) => {
            onChange(ev.target.checked ? "yes" : "no");
          }}
          onKeyDown={(ev) => {
            if (isDeleteOrBackspace(ev)) {
              ev.preventDefault();
              ev.stopPropagation();
              onChange(null); // set value back to unset
            }
          }}
          title={trans("TRISTATE_CHECKBOX_TOOLTIP")}
        />
        {type.checkbox_label_i18n ? trans_obj(type.checkbox_label_i18n) : null}
      </label>
    </div>
  );
}
