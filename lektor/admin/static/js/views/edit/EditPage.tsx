import React, {
  FormEvent,
  SetStateAction,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { Prompt } from "react-router-dom";

import { RecordProps } from "../../components/RecordComponent";
import { keyboardShortcutHandler } from "../../utils";
import { get, put } from "../../fetch";
import { trans, Translatable, trans_fallback, trans_format } from "../../i18n";
import {
  getWidgetComponentWithFallback,
  FieldBox,
  FieldRows,
  splitFields,
} from "../../widgets";
import { showErrorDialog } from "../../error-dialog";
import { Field, WidgetComponent } from "../../widgets/types";
import { EditPageActions } from "./EditPageActions";
import ToggleGroup from "../../components/ToggleGroup";
import { useGoToAdminPage } from "../../components/use-go-to-admin-page";

export type RawRecordInfo = {
  alt: string;
  can_be_deleted: boolean;
  default_template: string;
  exists: boolean;
  id: string;
  implied_attachment_type: string | null;
  is_attachment: boolean;
  label: string;
  label_i18n?: Translatable;
  path: string;
  slug_format: string;
  url_path: string;
};

type RecordDataModel = {
  alt: string;
  fields: Field[];
};

export type RawRecord = {
  datamodel: RecordDataModel;
  record_info: RawRecordInfo;
  data: Record<string, string>;
};

function legalFields(
  recordDataModel: Pick<RecordDataModel, "fields">,
  recordInfo: Pick<RawRecordInfo, "is_attachment">
) {
  function isLegalField(field: Field): boolean {
    switch (field.name) {
      case "_id":
      case "_path":
      case "_gid":
      case "_alt":
      case "_source_alt":
      case "_model":
      case "_attachment_for":
        return false;
      case "_attachment_type":
        return recordInfo.is_attachment;
    }
    return true;
  }
  return recordDataModel.fields.filter(isLegalField);
}

function getPlaceholderForField(
  recordInfo: RawRecordInfo,
  Widget: WidgetComponent,
  field: Field
): string | null {
  if (field.default !== null) {
    if (Widget.deserializeValue) {
      return Widget.deserializeValue(field.default, field.type);
    }
    return field.default;
  } else if (field.name === "_slug") {
    return recordInfo.slug_format;
  } else if (field.name === "_template") {
    return recordInfo.default_template;
  } else if (field.name === "_attachment_type") {
    return recordInfo.implied_attachment_type;
  }
  return null;
}

function getValueForField(
  recordData: Record<string, string>,
  Widget: WidgetComponent,
  field: Field
) {
  let value = recordData[field.name];
  if (value === undefined) {
    value = "";
    if (Widget.deserializeValue) {
      value = Widget.deserializeValue(value, field.type);
    }
  }
  return value;
}

function getValues({
  recordDataModel,
  recordInfo,
  recordData,
}: {
  recordData: Record<string, string>;
  recordDataModel: RecordDataModel | null;
  recordInfo: RawRecordInfo | null;
}): Record<string, string | null> {
  const rv: Record<string, string | null> = {};
  if (!recordDataModel || !recordInfo) {
    return rv;
  }
  legalFields(recordDataModel, recordInfo).forEach((field) => {
    let value: string | null = recordData[field.name];

    if (value !== undefined) {
      const Widget = getWidgetComponentWithFallback(field.type);
      if (Widget.serializeValue) {
        value = Widget.serializeValue(value, field.type);
      }
    } else {
      value = null;
    }

    rv[field.name] = value;
  });

  return rv;
}

function EditPage({ record }: Pick<RecordProps, "record">): JSX.Element | null {
  const form = useRef<HTMLFormElement | null>(null);
  // The deserialised record data.
  const [recordData, setRecordData] = useState<Record<string, string>>({});
  const [recordDataModel, setRecordDataModel] =
    useState<RecordDataModel | null>(null);
  const [recordInfo, setRecordnfo] = useState<RawRecordInfo | null>(null);
  const [hasPendingChanges, setHasPendingChanges] = useState(false);

  const goToAdminPage = useGoToAdminPage();

  const { path, alt } = record;

  useEffect(() => {
    let ignore = false;
    get("/rawrecord", { path, alt }).then(
      ({ datamodel, data, record_info }) => {
        if (!ignore) {
          // transform response data into actual data
          const recordData: Record<string, string> = {};
          legalFields(datamodel, record_info).forEach((field) => {
            const Widget = getWidgetComponentWithFallback(field.type);
            let value = data[field.name];
            if (value !== undefined) {
              if (Widget.deserializeValue) {
                value = Widget.deserializeValue(value, field.type);
              }
              recordData[field.name] = value;
            }
          });
          setRecordData(recordData);
          setRecordDataModel(datamodel);
          setRecordnfo(record_info);
          setHasPendingChanges(false);
        }
      },
      showErrorDialog
    );

    return () => {
      ignore = true;
    };
  }, [alt, path]);

  useEffect(() => {
    const onKeyPress = keyboardShortcutHandler(
      { key: "Control+s", mac: "Meta+s", preventDefault: true },
      () => {
        if (form.current?.reportValidity()) {
          form.current
            .querySelector<HTMLButtonElement>("button[type='submit']")
            ?.click();
        }
      }
    );
    window.addEventListener("keydown", onKeyPress);
    return () => window.removeEventListener("keydown", onKeyPress);
  }, []);

  const setFieldValue = useCallback(
    (fieldName: string, value: SetStateAction<string>) => {
      setRecordData((r) => ({
        ...r,
        [fieldName]: typeof value === "function" ? value(r[fieldName]) : value,
      }));
      setHasPendingChanges(true);
    },
    []
  );

  const saveChanges = useCallback(
    (ev: FormEvent) => {
      ev.preventDefault();
      const data = getValues({ recordDataModel, recordInfo, recordData });
      put("/rawrecord", { data, path, alt }).then(() => {
        setHasPendingChanges(false);
        goToAdminPage("preview", path, alt);
      }, showErrorDialog);
    },
    [alt, goToAdminPage, path, recordData, recordDataModel, recordInfo]
  );

  const renderFormField = useCallback(
    (field: Field) => {
      const Widget = getWidgetComponentWithFallback(field.type);
      if (!recordInfo) {
        return null;
      }
      // If alts_enabled is set, only show allow editing on alts (if true)
      // or on the primary (if false)
      const disabled = !(
        field.alts_enabled === null ||
        field.alts_enabled !== (recordInfo.alt === "_primary")
      );
      return (
        <FieldBox
          key={field.name}
          value={getValueForField(recordData, Widget, field)}
          placeholder={getPlaceholderForField(recordInfo, Widget, field)}
          field={field}
          setFieldValue={setFieldValue}
          disabled={disabled}
        />
      );
    },
    [recordData, recordInfo, setFieldValue]
  );

  if (!recordInfo || !recordDataModel) {
    // we have not loaded anything yet.
    return null;
  }

  const label = trans_fallback(recordInfo.label_i18n, recordInfo.label);

  const title = recordInfo.is_attachment
    ? trans_format("EDIT_ATTACHMENT_METADATA_OF", label)
    : trans_format("EDIT_PAGE_NAME", label);

  const fields = legalFields(recordDataModel, recordInfo);
  const [normalFields, systemFields] = splitFields(fields);

  return (
    <>
      {hasPendingChanges && <Prompt message={trans("UNLOAD_ACTIVE_TAB")} />}
      <h2>{title}</h2>
      <form ref={form} onSubmit={saveChanges}>
        <FieldRows fields={normalFields} renderFunc={renderFormField} />
        {systemFields.length > 0 && (
          <ToggleGroup
            groupTitle={trans("SYSTEM_FIELDS")}
            className="system-fields"
          >
            <FieldRows fields={systemFields} renderFunc={renderFormField} />
          </ToggleGroup>
        )}
        <EditPageActions
          record={record}
          recordInfo={recordInfo}
          hasPendingChanges={hasPendingChanges}
        />
      </form>
    </>
  );
}

export default EditPage;
