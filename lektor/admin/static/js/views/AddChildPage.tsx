import React, { ChangeEvent, Component, ReactNode } from "react";
import {
  getUrlRecordPathWithAlt,
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import { trans, Translatable, trans_format, trans_obj } from "../i18n";
import { formatUserLabel } from "../userLabel";
import { loadData } from "../fetch";
import { slugify } from "../slugify";
import { getWidgetComponentWithFallback } from "../widgets";
import { bringUpDialog } from "../richPromise";
import { SlugInputWidget } from "../widgets/SlugInputWidget";
import { Field } from "../widgets/types";

type Model = {
  id: string;
  name: string;
  name_i18n: Translatable;
  primary_field: Field;
};

type NewRecordInfo = {
  label: string;
  can_have_children: boolean;
  implied_model: Model;
  available_models: Record<string, Model>;
};

type State = {
  newChildInfo: NewRecordInfo | null;
  selectedModel: string;
  id: string;
  primary: string;
};

function getGoodDefaultModel(models: Record<string, Model>) {
  if (models.page !== undefined) {
    return "page";
  }
  return Object.keys(models).sort()[0];
}

function getAvailableModels(newChildInfo: NewRecordInfo) {
  const rv = [];
  for (const key in newChildInfo.available_models) {
    const model = newChildInfo.available_models[key];
    rv.push(model);
  }
  rv.sort((a, b) => {
    return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
  });
  return rv;
}

function FieldRow({ children }: { children: ReactNode }) {
  return (
    <div className="row field-row" key="_model">
      <div className="col-md-12">
        <dl className="field">{children}</dl>
      </div>
    </div>
  );
}

class AddChildPage extends Component<RecordProps, State> {
  constructor(props: RecordProps) {
    super(props);
    this.state = {
      newChildInfo: null,
      selectedModel: "",
      id: "",
      primary: "",
    };

    this.createRecord = this.createRecord.bind(this);
    this.onModelSelected = this.onModelSelected.bind(this);
  }

  componentDidMount() {
    this.syncDialog();
  }

  componentDidUpdate(prevProps: RecordProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.syncDialog();
    }
  }

  syncDialog() {
    loadData("/newrecord", { path: this.props.record.path }).then((resp) => {
      let selectedModel = resp.implied_model;
      if (!selectedModel) {
        selectedModel = getGoodDefaultModel(resp.available_models);
      }

      this.setState({
        newChildInfo: resp,
        selectedModel,
        id: "",
        primary: "",
      });
    }, bringUpDialog);
  }

  onValueChange(id: "id" | "primary", value: string) {
    const obj: Partial<State> = {};
    obj[id] = value;
    this.setState((state) => ({ ...state, [id]: value }));
  }

  onModelSelected(event: ChangeEvent<HTMLSelectElement>) {
    this.setState({
      selectedModel: event.target.value,
    });
  }

  getImpliedId(): string {
    return slugify(this.state.primary).toLowerCase();
  }

  getPrimaryField(): Field | undefined {
    const model = this.state.selectedModel;
    return this.state.newChildInfo?.available_models[model].primary_field;
  }

  createRecord() {
    const errMsg = (text: string) => {
      alert(trans("ERROR_PREFIX") + text);
    };

    const id = this.state.id || this.getImpliedId();
    if (!id) {
      errMsg(trans("ERROR_NO_ID_PROVIDED"));
      return;
    }

    const data: Record<string, string | null> = {};
    const params = { id: id, path: this.props.record.path, data: data };
    if (!this.state.newChildInfo?.implied_model) {
      data._model = this.state.selectedModel;
    }
    const primaryField = this.getPrimaryField();
    if (primaryField) {
      data[primaryField.name] = this.state.primary;
    }

    loadData("/newrecord", null, { json: params, method: "POST" }).then(
      (resp) => {
        if (resp.exists) {
          errMsg(trans_format("ERROR_PAGE_ID_DUPLICATE", id));
        } else if (!resp.valid_id) {
          errMsg(trans_format("ERROR_INVALID_ID", id));
        } else {
          const urlPath = getUrlRecordPathWithAlt(
            resp.path,
            this.props.record.alt
          );
          this.props.history.push(pathToAdminPage("edit", urlPath));
        }
      },
      bringUpDialog
    );
  }

  render() {
    const newChildInfo = this.state.newChildInfo;

    if (!newChildInfo) {
      return null;
    }
    const fields = [];
    const primaryField = this.getPrimaryField();
    if (primaryField) {
      let value = this.state.primary;
      const field = primaryField;
      const Widget = getWidgetComponentWithFallback(field.type);
      if (Widget.deserializeValue) {
        value = Widget.deserializeValue(value, field.type);
      }
      fields.push(
        <FieldRow key={field.name}>
          <dt>{formatUserLabel(field.label_i18n)}</dt>
          <dd>
            <Widget
              value={value || ""}
              onChange={this.onValueChange.bind(this, "primary")}
              type={field.type}
              field={field}
            />
          </dd>
        </FieldRow>
      );
    }

    return (
      <div className="edit-area">
        <h2>{trans_format("ADD_CHILD_PAGE_TO", newChildInfo.label)}</h2>
        <p>{trans("ADD_CHILD_PAGE_NOTE")}</p>
        {!newChildInfo.implied_model && (
          <FieldRow key="_model">
            <dt>{trans("MODEL")}</dt>
            <dd>
              <select
                value={this.state.selectedModel}
                className="form-control"
                onChange={this.onModelSelected}
              >
                {getAvailableModels(newChildInfo).map((model) => (
                  <option value={model.id} key={model.id}>
                    {trans_obj(model.name_i18n)}
                  </option>
                ))}
              </select>
            </dd>
          </FieldRow>
        )}
        {fields}
        <FieldRow key="_id">
          <dt>{formatUserLabel(trans("ID"))}</dt>
          <dd>
            <SlugInputWidget
              value={this.state.id}
              placeholder={this.getImpliedId()}
              onChange={this.onValueChange.bind(this, "id")}
              type={{ widget: "slug", name: "slug", size: "normal" }}
            />
          </dd>
        </FieldRow>
        <div className="actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={this.createRecord}
          >
            {trans("CREATE_CHILD_PAGE")}
          </button>
        </div>
      </div>
    );
  }
}

export default AddChildPage;
