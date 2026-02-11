import { RecordPath, RecordAlternative } from "../context/record-context";
import type { Translatable } from "../i18n";

export interface Alternative {
  alt: RecordAlternative;
  is_primary: boolean;
  primary_overlay: boolean;
  name_i18n: Translatable;
  exists: boolean;
}

export interface RecordChild {
  id: string;
  path: RecordPath;
  label: string;
  label_i18n: Translatable;
  visible: boolean;
}

export interface RecordAttachment {
  id: string;
  path: RecordPath;
  type: string;
  label_i18n: Translatable;
}

// Returned by /recordinfo
export interface RecordInfo {
  id: string;
  path: RecordPath;
  label_i18n?: Translatable;
  exists: boolean;
  is_attachment: boolean;
  attachments: RecordAttachment[];
  children: RecordChild[];
  alts: Alternative[];
  can_have_children: boolean;
  can_have_attachments: boolean;
  can_be_deleted: boolean;
}
