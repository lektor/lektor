import React, { ChangeEvent, useCallback } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { getInputClass, WidgetProps } from "./types";

export function MultiLineTextInputWidget({
  type,
  value,
  placeholder,
  disabled,
  onChange: onChangeProp,
}: WidgetProps) {
  const onChange = useCallback(
    (event: ChangeEvent<HTMLTextAreaElement>) => {
      onChangeProp(event.target.value);
    },
    [onChangeProp]
  );

  return (
    <div>
      <TextareaAutosize
        className={getInputClass(type)}
        onChange={onChange}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
      />
    </div>
  );
}
