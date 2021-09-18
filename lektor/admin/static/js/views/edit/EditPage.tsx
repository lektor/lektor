import React, { Component, createRef, FormEvent, RefObject } from "react";
import { Prompt } from "react-router-dom";

import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../../components/RecordComponent";
import { keyboardShortcutHandler } from "../../utils";
import { loadData } from "../../fetch";
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

type State = {
  // The deserialised record data.
  recordData: Record<string, string>;
  recordDataModel: RecordDataModel | null;
  recordInfo: RawRecordInfo | null;
  hasPendingChanges: boolean;
};

type RawRecord = {
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
}: State): Record<string, string | null> {
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

type Props = Pick<RecordProps, "record" | "history">;

class EditPage extends Component<Props, State> {
  form: RefObject<HTMLFormElement>;

  onKeyPress: (ev: KeyboardEvent) => void;

  constructor(props: Props) {
    super(props);

    this.state = {
      recordData: {},
      recordDataModel: null,
      recordInfo: null,
      hasPendingChanges: false,
    };
    this.form = createRef();
    this.onKeyPress = keyboardShortcutHandler(
      { key: "Control+s", mac: "Meta+s", preventDefault: true },
      () => {
        if (this.form.current?.reportValidity()) {
          this.saveChanges();
        }
      }
    );

    this.setFieldValue = this.setFieldValue.bind(this);
    this.saveChanges = this.saveChanges.bind(this);
    this.renderFormField = this.renderFormField.bind(this);
  }

  componentDidMount() {
    this.syncEditor();
    window.addEventListener("keydown", this.onKeyPress);
  }

  componentDidUpdate(prevProps: Props) {
    if (
      prevProps.record.path !== this.props.record.path ||
      prevProps.record.alt !== this.props.record.alt
    ) {
      this.syncEditor();
    }
  }

  componentWillUnmount() {
    window.removeEventListener("keydown", this.onKeyPress);
  }

  syncEditor() {
    loadData("/rawrecord", {
      path: this.props.record.path,
      alt: this.props.record.alt,
    }).then((resp: RawRecord) => {
      // transform resp.data into actual data
      const recordData: Record<string, string> = {};
      legalFields(resp.datamodel, resp.record_info).forEach((field) => {
        const Widget = getWidgetComponentWithFallback(field.type);
        let value = resp.data[field.name];
        if (value !== undefined) {
          if (Widget.deserializeValue) {
            value = Widget.deserializeValue(value, field.type);
          }
          recordData[field.name] = value;
        }
      });
      this.setState({
        recordData,
        recordDataModel: resp.datamodel,
        recordInfo: resp.record_info,
        hasPendingChanges: false,
      });
    }),
      showErrorDialog;
  }

  setFieldValue(field: Field, value: string, uiChange = false) {
    this.setState((state) => ({
      recordData: { ...state.recordData, [field.name]: value || "" },
      hasPendingChanges: !uiChange || state.hasPendingChanges,
    }));
  }

  saveChanges(event?: FormEvent) {
    event?.preventDefault();
    const { alt, path } = this.props.record;
    if (path === null) {
      return;
    }
    loadData("/rawrecord", null, {
      json: { data: getValues(this.state), path, alt },
      method: "PUT",
    }).then(() => {
      this.setState({ hasPendingChanges: false }, () => {
        this.props.history.push(
          pathToAdminPage(
            "preview",
            getUrlRecordPath(path, this.props.record.alt)
          )
        );
      });
    }, showErrorDialog);
  }

  renderFormField(field: Field) {
    const Widget = getWidgetComponentWithFallback(field.type);
    const { recordInfo, recordData } = this.state;
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
        setFieldValue={this.setFieldValue}
        disabled={disabled}
      />
    );
  }

  render() {
    const { recordInfo, recordDataModel, hasPendingChanges } = this.state;
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
      <div className="edit-area">
        {hasPendingChanges && <Prompt message={trans("UNLOAD_ACTIVE_TAB")} />}
        <h2>{title}</h2>
        <form ref={this.form} onSubmit={this.saveChanges}>
          <FieldRows fields={normalFields} renderFunc={this.renderFormField} />
          {systemFields.length > 0 && (
            <ToggleGroup
              groupTitle={trans("SYSTEM_FIELDS")}
              defaultVisibility={false}
              className="system-fields"
            >
              <FieldRows
                fields={systemFields}
                renderFunc={this.renderFormField}
              />
            </ToggleGroup>
          )}
          <EditPageActions
            record={this.props.record}
            recordInfo={recordInfo}
            hasPendingChanges={hasPendingChanges}
          />
        </form>
      </div>
    );
  }
}

export default EditPage;
