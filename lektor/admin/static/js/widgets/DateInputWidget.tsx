import React from "react";
import { WidgetProps } from "./types";
import { trans } from "../i18n";
import InputWidgetBase from "./InputWidgetBase";

const parseInteger = (s: string) => Number.parseInt(s, 10);

export function isValidDate(year: number, month: number, day: number) {
  const date = new Date(year, month - 1, day);
  return (
    date.getFullYear() === year &&
    date.getMonth() === month - 1 &&
    date.getDate() === day
  );
}

const DATE_RE = /^\s*(?<year>\d{4})-(?<month>\d{1,2})-(?<day>\d{1,2})\s*$/;

export function validateDate(value: string): string | null {
  if (!value) {
    return null;
  }

  const groups = value.match(DATE_RE)?.groups;
  if (
    groups &&
    isValidDate(
      parseInteger(groups.year),
      parseInteger(groups.month),
      parseInteger(groups.day)
    )
  ) {
    return null;
  }

  return trans("ERROR_INVALID_DATE");
}
const REVERSE_DATE_RE =
  /^(?<day>\d{1,2})\.(?<month>\d{1,2})\.(?<year>\d{4})\s*$/;

const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);

export function postprocessDate(value: string) {
  value = value.trim();
  const groups = value.match(REVERSE_DATE_RE)?.groups;
  if (groups) {
    const day = parseInteger(groups.day);
    const month = parseInteger(groups.month);
    const year = parseInteger(groups.year);
    return `${year}-${pad(month)}-${pad(day)}`;
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
