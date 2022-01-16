import { createContext } from "react";
import { PageName } from "../components/RecordComponent";

/** The currently rendered page of the Lektor admin interface. */
export const PageContext = createContext<PageName>("edit");
