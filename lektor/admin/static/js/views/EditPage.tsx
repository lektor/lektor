import React, { createRef, FormEvent, RefObject } from "react";
import { Prompt } from "react-router-dom";

import RecordComponent, { RecordProps } from "../components/RecordComponent";
import { isMetaKey } from "../utils";
import { loadData } from "../fetch";
import { trans, Translatable } from "../i18n";
import {
  getWidgetComponentWithFallback,
  FieldBox,
  FieldRows,
} from "../widgets";
import { bringUpDialog } from "../richPromise";
import { Field, WidgetComponent } from "../widgets/types";

type RawRecordInfo = {
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

class EditPage extends RecordComponent<RecordProps, State> {
  form: RefObject<HTMLFormElement>;

  constructor(props: RecordProps) {
    super(props);

    this.state = {
      recordData: {},
      recordDataModel: null,
      recordInfo: null,
      hasPendingChanges: false,
    };
    this.form = createRef();

    this.onKeyPress = this.onKeyPress.bind(this);
    this.setFieldValue = this.setFieldValue.bind(this);
    this.saveChanges = this.saveChanges.bind(this);
    this.renderFormField = this.renderFormField.bind(this);
    this.deleteRecord = this.deleteRecord.bind(this);
  }

  componentDidMount() {
    this.syncEditor();
    window.addEventListener("keydown", this.onKeyPress);
  }

  componentDidUpdate(prevProps: RecordProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.syncEditor();
    }
  }

  componentWillUnmount() {
    window.removeEventListener("keydown", this.onKeyPress);
  }

  onKeyPress(event: KeyboardEvent) {
    // Command+s/Ctrl+s to save
    if (event.key === "s" && isMetaKey(event)) {
      event.preventDefault();
      const form = this.form.current;
      if (form && form.reportValidity()) {
        this.saveChanges();
      }
    }
  }

  syncEditor() {
    loadData("/rawrecord", {
      path: this.getRecordPath(),
      alt: this.getRecordAlt(),
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
      bringUpDialog;
  }

  setFieldValue(field: Field, value: string, uiChange = false) {
    const rd = { ...this.state.recordData, [field.name]: value || "" };
    this.setState({
      recordData: rd,
      hasPendingChanges: !uiChange,
    });
  }

  getValues() {
    const rv: Record<string, string | null> = {};
    const { recordDataModel, recordInfo, recordData } = this.state;
    if (!recordDataModel || !recordInfo || !recordData) {
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

  saveChanges(event?: FormEvent) {
    if (event) {
      event.preventDefault();
    }

    const path = this.getRecordPath();
    if (path === null) {
      return;
    }
    const alt = this.getRecordAlt();
    const newData = this.getValues();
    loadData("/rawrecord", null, {
      json: { data: newData, path: path, alt: alt },
      method: "PUT",
    }).then(() => {
      this.setState(
        {
          hasPendingChanges: false,
        },
        () => {
          this.transitionToAdminPage(
            "preview",
            this.getUrlRecordPathWithAlt(path)
          );
        }
      );
    }, bringUpDialog);
  }

  deleteRecord() {
    this.transitionToAdminPage("delete", this.getUrlRecordPathWithAlt());
  }

  getValueForField(Widget: WidgetComponent, field: Field) {
    let value = this.state.recordData[field.name];
    if (value === undefined) {
      value = "";
      if (Widget.deserializeValue) {
        value = Widget.deserializeValue(value, field.type);
      }
    }
    return value;
  }

  renderFormField(field: Field) {
    const Widget = getWidgetComponentWithFallback(field.type);
    const { recordInfo } = this.state;
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
        value={this.getValueForField(Widget, field)}
        placeholder={getPlaceholderForField(recordInfo, Widget, field)}
        field={field}
        setFieldValue={this.setFieldValue}
        disabled={disabled}
      />
    );
  }

  render() {
    // we have not loaded anything yet.
    const { recordInfo, recordDataModel } = this.state;
    if (recordInfo === null || recordDataModel === null) {
      return null;
    }

    const title = recordInfo.is_attachment
      ? trans("EDIT_ATTACHMENT_METADATA_OF")
      : trans("EDIT_PAGE_NAME");

    const label = recordInfo.label_i18n
      ? trans(recordInfo.label_i18n)
      : recordInfo.label;

    const fields = legalFields(recordDataModel, recordInfo);

    return (
      <div className="edit-area">
        {this.state.hasPendingChanges && (
          <Prompt message={() => trans("UNLOAD_ACTIVE_TAB")} />
        )}
        <h2>{title.replace("%s", label)}</h2>
        <form ref={this.form} onSubmit={this.saveChanges}>
          <FieldRows fields={fields} renderFunc={this.renderFormField} />
          <div className="actions">
            <button type="submit" className="btn btn-primary">
              {trans("SAVE_CHANGES")}
            </button>
            {recordInfo.can_be_deleted ? (
              <button
                type="button"
                className="btn btn-default"
                onClick={this.deleteRecord}
              >
                {trans("DELETE")}
              </button>
            ) : null}
          </div>
        </form>
      </div>
    );
  }
}

export default EditPage;
