import { createContext } from "react";

export const PAGE_NAMES = [
  "edit",
  "delete",
  "preview",
  "add-child",
  "upload",
] as const;
export type PageName = typeof PAGE_NAMES[number];

/** The currently rendered page of the Lektor admin interface. */
export const PageContext = createContext<PageName>("edit");
