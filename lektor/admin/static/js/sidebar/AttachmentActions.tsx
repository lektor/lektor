import React, { PureComponent } from "react";
import {
  getUrlRecordPathWithAlt,
  RecordProps,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { RecordInfo } from "../components/types";
import { trans } from "../i18n";

type Props = RecordProps & { recordInfo: RecordInfo };

export default class AttachmentActions extends PureComponent<Props, unknown> {
  render() {
    const attachments = this.props.recordInfo.attachments;
    return (
      <div className="section">
        <h3>{trans("ATTACHMENTS")}</h3>
        <ul className="nav record-attachments">
          {attachments.length > 0 ? (
            attachments.map((atch) => {
              const urlPath = getUrlRecordPathWithAlt(
                atch.path,
                this.props.record.alt
              );
              return (
                <li key={atch.id}>
                  <Link to={`${urlPath}/edit`}>
                    {atch.id} ({atch.type})
                  </Link>
                </li>
              );
            })
          ) : (
            <li key="_missing">
              <em>{trans("NO_ATTACHMENTS")}</em>
            </li>
          )}
        </ul>
      </div>
    );
  }
}
