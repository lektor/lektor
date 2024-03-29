import { Translatable } from "../../i18n";
import { Field } from "../../widgets/types";

export interface Model {
  id: string;
  name: string;
  name_i18n: Translatable;
  primary_field: Field;
}

export interface NewRecordInfo {
  label: string;
  can_have_children: boolean;
  implied_model: string | null;
  available_models: Record<string, Model>;
}
