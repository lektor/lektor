import React, { ChangeEvent, ReactNode } from "react";
import { formatUserLabel } from "../userLabel";
import { getInputClass, WidgetProps } from "./types";

export default function InputWidgetBase(
  props: WidgetProps & {
    onChange: (val: string) => void;
    postprocessValue?: (val: string) => string;
    inputAddon?: ReactNode;
    inputType: string;
    validate?: (val: string) => string | null;
  }
) {
  const {
    type,
    value,
    onChange,
    postprocessValue,
    inputAddon,
    inputType,
    validate,
    disabled,
    placeholder,
  } = props;
  let help = null;
  let className = "input-group";
  function onChangeHandler(event: ChangeEvent<HTMLInputElement>) {
    let value = event.target.value;
    if (postprocessValue) {
      value = postprocessValue(value);
    }
    onChange(value);
  }

  const failure = validate ? validate(value || "") : null;
  const setValidity = (el: HTMLInputElement | null) => {
    el?.setCustomValidity(failure || "");
  };
  if (failure !== null) {
    className += " has-feedback has-error";
    const valClassName = "validation-block validation-block-error";
    help = <div className={valClassName}>{failure}</div>;
  }

  let addon = null;
  const configuredAddon = type.addon_label_i18n;
  if (configuredAddon) {
    addon = formatUserLabel(configuredAddon);
  } else if (inputAddon) {
    addon = inputAddon;
  }

  return (
    <div className="form-group">
      <div className={className}>
        <input
          ref={setValidity}
          type={inputType}
          disabled={disabled}
          placeholder={placeholder}
          className={getInputClass(type)}
          onChange={onChangeHandler}
          value={value || ""}
        />
        {addon ? <span className="input-group-text">{addon}</span> : null}
      </div>
      {help}
    </div>
  );
}
