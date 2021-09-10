import React, { useCallback, useEffect, useState } from "react";
import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../../components/RecordComponent";
import { trans, trans_format } from "../../i18n";
import { loadData } from "../../fetch";
import { slugify } from "../../slugify";
import { showErrorDialog } from "../../error-dialog";
import { NewRecordInfo } from "./types";
import AvailableModels from "./AvailableModels";
import PrimaryField from "./PrimaryFieldRow";
import Slug from "./Slug";
import { useHistory } from "react-router";

/** Show an alert with the given error message. */
const alertErr = (text: string) => {
  alert(trans("ERROR_PREFIX") + text);
};

type Props = Pick<RecordProps, "record">;

function AddChildPage({ record }: Props) {
  const [newChildInfo, setNewChildInfo] = useState<NewRecordInfo | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [id, setId] = useState<string>("");
  const [primary, setPrimary] = useState<string>("");
  const { alt, path } = record;

  useEffect(() => {
    let ignore = false;
    loadData("/newrecord", { path }).then((resp: NewRecordInfo) => {
      if (!ignore) {
        const defaultModel = resp.available_models.page
          ? "page"
          : Object.keys(resp.available_models).sort()[0];
        const selectedModel = resp.implied_model ?? defaultModel;
        setNewChildInfo(resp);
        setId("");
        setPrimary("");
        setSelectedModel(selectedModel);
      }
    }, showErrorDialog);

    return () => {
      ignore = true;
    };
  }, [path]);

  const primaryField =
    newChildInfo?.available_models[selectedModel]?.primary_field;

  const history = useHistory();

  const createRecord = useCallback(() => {
    const currentId = id || slugify(primary).toLowerCase();
    if (!currentId) {
      alertErr(trans("ERROR_NO_ID_PROVIDED"));
      return;
    }

    const data: Record<string, string> = {};
    if (!newChildInfo?.implied_model) {
      data._model = selectedModel;
    }
    if (primaryField) {
      data[primaryField.name] = primary;
    }

    loadData("/newrecord", null, {
      json: { id: currentId, path, data },
      method: "POST",
    }).then((resp) => {
      if (resp.exists) {
        alertErr(trans_format("ERROR_PAGE_ID_DUPLICATE", currentId));
      } else if (!resp.valid_id) {
        alertErr(trans_format("ERROR_INVALID_ID", currentId));
      } else {
        const urlPath = getUrlRecordPath(resp.path, alt);
        history.push(pathToAdminPage("edit", urlPath));
      }
    }, showErrorDialog);
  }, [
    alt,
    history,
    newChildInfo,
    id,
    path,
    primary,
    primaryField,
    selectedModel,
  ]);

  if (!newChildInfo) {
    return null;
  }

  return (
    <div className="edit-area">
      <h2>{trans_format("ADD_CHILD_PAGE_TO", newChildInfo.label)}</h2>
      <p>{trans("ADD_CHILD_PAGE_NOTE")}</p>
      {!newChildInfo.implied_model && (
        <AvailableModels
          newChildInfo={newChildInfo}
          selected={selectedModel}
          setSelected={setSelectedModel}
        />
      )}
      {primaryField && (
        <PrimaryField
          primary={primary}
          setPrimary={setPrimary}
          field={primaryField}
        />
      )}
      <Slug
        id={id}
        placeholder={slugify(primary).toLowerCase()}
        setId={setId}
      />
      <div className="actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={createRecord}
        >
          {trans("CREATE_CHILD_PAGE")}
        </button>
      </div>
    </div>
  );
}

export default AddChildPage;
