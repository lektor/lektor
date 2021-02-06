import type { Translatable } from "../i18n";

export type Alternative = {
  alt: string;
  is_primary: boolean;
  primary_overlay: boolean;
  name_i18n: Translatable;
  exists: boolean;
};

export type RecordChild = {
  id: string;
  path: string;
  label: string;
  label_i18n: Translatable;
  visible: boolean;
};

export type RecordAttachment = {
  id: string;
  path: string;
  type: string;
};

// Returned by /recordinfo
export type RecordInfo = {
  id: string;
  path: string;
  label_i18n?: Translatable;
  exists: boolean;
  is_attachment: boolean;
  attachments: RecordAttachment[];
  children: RecordChild[];
  alts: Alternative[];
  can_have_children: boolean;
  can_have_attachments: boolean;
  can_be_deleted: boolean;
};
