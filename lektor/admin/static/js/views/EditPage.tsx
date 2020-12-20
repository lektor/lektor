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

type RecordInfo = {
  can_be_deleted: boolean;
  exists: boolean;
  is_attachment: boolean;
  label: string;
  label_i18n?: Translatable;
};

type RecordDataModel = {
  alt: string;
  fields: Field[];
};

type State = {
  recordData: Record<string, string> | null;
  recordDataModel: RecordDataModel | null;
  recordInfo: RecordInfo | null;
  hasPendingChanges: boolean;
};

type RawRecord = {
  datamodel: RecordDataModel;
  record_info: RecordInfo;
  data: Record<string, string>;
};

function isIllegalField(
  field: Field,
  recordInfo: Pick<RecordInfo, "is_attachment">
): boolean {
  switch (field.name) {
    case "_id":
    case "_path":
    case "_gid":
    case "_alt":
    case "_source_alt":
    case "_model":
    case "_attachment_for":
      return true;
    case "_attachment_type":
      return !recordInfo.is_attachment;
  }
  return false;
}

class EditPage extends RecordComponent<unknown, State> {
  form: RefObject<HTMLFormElement>;

  constructor(props: RecordProps) {
    super(props);

    this.state = {
      recordData: null,
      recordDataModel: null,
      recordInfo: null,
      hasPendingChanges: false,
    };
    this.onKeyPress = this.onKeyPress.bind(this);
    this.setFieldValue = this.setFieldValue.bind(this);
    this.form = createRef();
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
      resp.datamodel.fields.forEach((field) => {
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
    const rv = {};
    this.state.recordDataModel.fields.forEach((field) => {
      if (isIllegalField(field, this.state.recordInfo)) {
        return;
      }

      let value = this.state.recordData[field.name];

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

  getPlaceholderForField(Widget: WidgetComponent, field: Field) {
    if (field.default !== null) {
      if (Widget.deserializeValue) {
        return Widget.deserializeValue(field.default, field.type);
      }
      return field.default;
    } else if (field.name === "_slug") {
      return this.state.recordInfo.slug_format;
    } else if (field.name === "_template") {
      return this.state.recordInfo.default_template;
    } else if (field.name === "_attachment_type") {
      return this.state.recordInfo.implied_attachment_type;
    }
    return null;
  }

  renderFormField(field) {
    const Widget = getWidgetComponentWithFallback(field.type);
    return (
      <FieldBox
        key={field.name}
        value={this.getValueForField(Widget, field)}
        placeholder={this.getPlaceholderForField(Widget, field)}
        field={field}
        setFieldValue={this.setFieldValue}
        disabled={
          !(
            field.alts_enabled == null ||
            field.alts_enabled ^ (this.state.recordInfo.alt === "_primary")
          )
        }
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

    const fields = recordDataModel.fields.filter(
      (f) => !isIllegalField(f, recordInfo)
    );
    return (
      <div className="edit-area">
        {this.state.hasPendingChanges && (
          <Prompt message={() => trans("UNLOAD_ACTIVE_TAB")} />
        )}
        <h2>{title.replace("%s", label)}</h2>
        <form ref={this.form} onSubmit={this.saveChanges.bind(this)}>
          <FieldRows
            fields={fields}
            renderFunc={this.renderFormField.bind(this)}
          />
          <div className="actions">
            <button type="submit" className="btn btn-primary">
              {trans("SAVE_CHANGES")}
            </button>
            {recordInfo.can_be_deleted ? (
              <button
                type="button"
                className="btn btn-default"
                onClick={this.deleteRecord.bind(this)}
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
