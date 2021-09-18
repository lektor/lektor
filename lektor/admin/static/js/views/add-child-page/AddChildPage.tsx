import React, { Component } from "react";
import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../../components/RecordComponent";
import { trans, trans_format } from "../../i18n";
import { loadData } from "../../fetch";
import { slugify } from "../../slugify";
import { showErrorDialog } from "../../error-dialog";
import { Field } from "../../widgets/types";
import { NewRecordInfo, Model } from "./types";
import AvailableModels from "./AvailableModels";
import PrimaryField from "./PrimaryFieldRow";
import Slug from "./Slug";

type State = {
  newChildInfo: NewRecordInfo | null;
  selectedModel: string;
  id: string;
  primary: string;
};

function getGoodDefaultModel(models: Record<string, Model>): string {
  return models.page ? "page" : Object.keys(models).sort()[0];
}

/** Show an alert with the given error message. */
const alertErr = (text: string) => {
  alert(trans("ERROR_PREFIX") + text);
};

type Props = Pick<RecordProps, "record" | "history">;

class AddChildPage extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      newChildInfo: null,
      selectedModel: "",
      id: "",
      primary: "",
    };

    this.createRecord = this.createRecord.bind(this);
  }

  componentDidMount() {
    this.syncDialog();
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.record.path !== this.props.record.path) {
      this.syncDialog();
    }
  }

  syncDialog() {
    loadData("/newrecord", { path: this.props.record.path }).then(
      (resp: NewRecordInfo) => {
        const selectedModel =
          resp.implied_model ?? getGoodDefaultModel(resp.available_models);
        this.setState({
          newChildInfo: resp,
          selectedModel,
          id: "",
          primary: "",
        });
      },
      showErrorDialog
    );
  }

  getPrimaryField(): Field | undefined {
    const model = this.state.selectedModel;
    return this.state.newChildInfo?.available_models[model].primary_field;
  }

  createRecord() {
    const id = this.state.id || slugify(this.state.primary).toLowerCase();
    if (!id) {
      alertErr(trans("ERROR_NO_ID_PROVIDED"));
      return;
    }

    const data: Record<string, string> = {};
    if (!this.state.newChildInfo?.implied_model) {
      data._model = this.state.selectedModel;
    }
    const primaryField = this.getPrimaryField();
    if (primaryField) {
      data[primaryField.name] = this.state.primary;
    }

    loadData("/newrecord", null, {
      json: { id, path: this.props.record.path, data },
      method: "POST",
    }).then((resp) => {
      if (resp.exists) {
        alertErr(trans_format("ERROR_PAGE_ID_DUPLICATE", id));
      } else if (!resp.valid_id) {
        alertErr(trans_format("ERROR_INVALID_ID", id));
      } else {
        const urlPath = getUrlRecordPath(resp.path, this.props.record.alt);
        this.props.history.push(pathToAdminPage("edit", urlPath));
      }
    }, showErrorDialog);
  }

  render() {
    const { newChildInfo, id, primary, selectedModel } = this.state;
    if (!newChildInfo) {
      return null;
    }
    const primaryField = this.getPrimaryField();

    return (
      <div className="edit-area">
        <h2>{trans_format("ADD_CHILD_PAGE_TO", newChildInfo.label)}</h2>
        <p>{trans("ADD_CHILD_PAGE_NOTE")}</p>
        {!newChildInfo.implied_model && (
          <AvailableModels
            newChildInfo={newChildInfo}
            selected={selectedModel}
            setSelected={(selectedModel) => this.setState({ selectedModel })}
          />
        )}
        {primaryField && (
          <PrimaryField
            primary={primary}
            setPrimary={(primary) => this.setState({ primary })}
            field={primaryField}
          />
        )}
        <Slug
          id={id}
          placeholder={slugify(primary).toLowerCase()}
          setId={(id) => this.setState({ id })}
        />
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
