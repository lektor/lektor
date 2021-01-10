import React from "react";
import { WidgetProps } from "./types";
import { trans } from "../i18n";
import InputWidgetBase from "./InputWidgetBase";

function isValidDate(year: number, month: number, day: number) {
  const date = new Date(year, month - 1, day);
  if (
    date.getFullYear() === year &&
    date.getMonth() === month - 1 &&
    date.getDate() === day
  ) {
    return true;
  }
  return false;
}

function validateDate(value: string) {
  if (!value) {
    return null;
  }

  const match = value.match(/^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$/);
  if (
    match &&
    isValidDate(
      parseInt(match[1], 10),
      parseInt(match[2], 10),
      parseInt(match[3], 10)
    )
  ) {
    return null;
  }

  return trans("ERROR_INVALID_DATE");
}

function postprocessDate(value: string) {
  value = value.trim();
  const match = value.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$/);
  let day, month, year;
  if (match) {
    day = parseInt(match[1], 10);
    month = parseInt(match[2], 10);
    year = parseInt(match[3], 10);
    return (
      year +
      "-" +
      (month < 10 ? "0" : "") +
      month +
      "-" +
      (day < 10 ? "0" : "") +
      day
    );
  }
  return value;
}

export function DateInputWidget(props: WidgetProps) {
  return (
    <InputWidgetBase
      inputType="date"
      inputAddon={<i className="fa fa-calendar" />}
      postprocessValue={postprocessDate}
      validate={validateDate}
      {...props}
    />
  );
}
