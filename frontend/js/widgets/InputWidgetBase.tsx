import React, { ChangeEvent, useCallback } from "react";
import { formatUserLabel } from "../userLabel";
import { getInputClass, WidgetProps } from "./types";

export default function InputWidgetBase({
  type,
  value,
  onChange,
  postprocessValue,
  inputAddon,
  inputType,
  validate,
  disabled,
  placeholder,
}: WidgetProps & {
  postprocessValue?: (val: string) => string;
  inputAddon: JSX.Element | string;
  inputType: string;
  validate?: (val: string) => string | null;
}): JSX.Element {
  const onChangeHandler = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      let value = event.target.value;
      if (postprocessValue) {
        value = postprocessValue(value);
      }
      onChange(value);
    },
    [onChange, postprocessValue]
  );

  const failure = validate ? validate(value) : null;
  const setValidity = (el: HTMLInputElement | null) => {
    el?.setCustomValidity(failure ?? "");
  };

  const configuredAddon = type.addon_label_i18n;
  const addon = configuredAddon ? formatUserLabel(configuredAddon) : inputAddon;

  return (
    <>
      <div className="input-group">
        <input
          ref={setValidity}
          type={inputType}
          disabled={disabled}
          placeholder={placeholder}
          className={getInputClass(type)}
          onChange={onChangeHandler}
          value={value || ""}
        />
        <span className="input-group-text">{addon}</span>
      </div>
      {failure !== null && (
        <div className={"validation-block validation-block-error"}>
          {failure}
        </div>
      )}
    </>
  );
}
