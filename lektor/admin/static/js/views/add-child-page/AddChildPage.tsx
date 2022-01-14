import React, { useCallback, useEffect, useState } from "react";
import { RecordProps } from "../../components/RecordComponent";
import { trans, trans_format } from "../../i18n";
import { get, post } from "../../fetch";
import { slugify } from "../../slugify";
import { showErrorDialog } from "../../error-dialog";
import { NewRecordInfo } from "./types";
import AvailableModels from "./AvailableModels";
import PrimaryField from "./PrimaryFieldRow";
import Slug from "./Slug";
import { useGoToAdminPage } from "../../components/use-go-to-admin-page";

/** Show an alert with the given error message. */
const alertErr = (text: string) => {
  alert(trans("ERROR_PREFIX") + text);
};

type Props = Pick<RecordProps, "record">;

function AddChildPage({ record }: Props): JSX.Element | null {
  const [newChildInfo, setNewChildInfo] = useState<NewRecordInfo | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [id, setId] = useState<string>("");
  const [primary, setPrimary] = useState<string>("");
  const { alt, path } = record;

  useEffect(() => {
    let ignore = false;
    get("/newrecord", { path }).then((resp) => {
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

  const goToAdminPage = useGoToAdminPage();

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

    post("/newrecord", null, { id: currentId, path, data }).then(
      ({ exists, valid_id, path }) => {
        if (exists) {
          alertErr(trans_format("ERROR_PAGE_ID_DUPLICATE", currentId));
        } else if (!valid_id) {
          alertErr(trans_format("ERROR_INVALID_ID", currentId));
        } else {
          goToAdminPage("edit", path, alt);
        }
      },
      showErrorDialog
    );
  }, [
    alt,
    goToAdminPage,
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
    <>
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
    </>
  );
}

export default AddChildPage;
