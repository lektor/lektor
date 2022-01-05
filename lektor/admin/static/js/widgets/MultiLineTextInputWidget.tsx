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

  const recalculateSize = useCallback(() => {
    const node = textarea.current;
    if (node) {
      node.style.height = "auto";
      node.style.height = node.scrollHeight + "px";
    }
  }, []);

  const onChange = useCallback(
    (event: ChangeEvent<HTMLTextAreaElement>) => {
      onChangeProp(event.target.value);
    },
    [onChangeProp]
  );

  useEffect(() => {
    recalculateSize();
  }, [recalculateSize, value]);

  useEffect(() => {
    window.addEventListener("resize", recalculateSize);
    return () => {
      window.removeEventListener("resize", recalculateSize);
    };
  }, [recalculateSize]);

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
