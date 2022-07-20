import fitTextarea from "fit-textarea";
import React, { ChangeEvent, useCallback, useEffect, useRef } from "react";
import { getInputClass, WidgetProps } from "./types";

export function MultiLineTextInputWidget({
  type,
  value,
  placeholder,
  disabled,
  onChange: onChangeProp,
}: WidgetProps) {
  const textarea = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (textarea?.current) {
      fitTextarea.watch(textarea?.current);
    }
  }, []);

  const onChange = useCallback(
    (event: ChangeEvent<HTMLTextAreaElement>) => {
      onChangeProp(event.target.value);
    },
    [onChangeProp]
  );

  return (
    <div>
      <textarea
        ref={textarea}
        className={getInputClass(type)}
        onChange={onChange}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
      />
    </div>
  );
}
