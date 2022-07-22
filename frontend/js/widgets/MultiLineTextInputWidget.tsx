import React, { ChangeEvent } from "react";
import { getInputClass, WidgetProps } from "./types";

export function MultiLineTextInputWidget({
  type,
  value,
  placeholder,
  disabled,
  onChange: onChangeProp,
}: WidgetProps) {
  const onChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    onChangeProp(event.target.value);
  };

  /* How this works
   *
   * The idea is ripped off from here:
   *
   *   https://css-tricks.com/the-cleanest-trick-for-autogrowing-textareas/
   *
   * We stack an (invisible) <div> under our <textarea> in a container
   * with display: grid.
   *
   * The issue we are trying to solve is that <textarea>s do not expand
   * when content is added to them.  However, <div>s do!
   *
   * The contents of the <textarea> is duplicated to the <div>. The
   * grid layout ensures that when the <div> expands, the <textarea> is
   * expanded to match.
   */
  return (
    <div className="text-widget">
      <div className="text-widget__replica">{value}</div>
      <textarea
        className={`${getInputClass(type)} text-widget__textarea`}
        onChange={onChange}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
      />
    </div>
  );
}
