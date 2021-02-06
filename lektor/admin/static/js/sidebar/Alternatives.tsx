import React, { PureComponent } from "react";
import {
  getUrlRecordPathWithAlt,
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import Link from "../components/Link";
import { Alternative } from "../components/types";
import { trans } from "../i18n";

type Props = RecordProps & { recordAlts: Alternative[] };

export default class Alternatives extends PureComponent<Props, unknown> {
  render() {
    const { recordAlts } = this.props;
    if (recordAlts.length < 2) {
      return null;
    }

    const items = recordAlts.map((item) => {
      let title = trans(item.name_i18n);
      let className = "alt";
      if (item.is_primary) {
        title += " (" + trans("PRIMARY_ALT") + ")";
      } else if (item.primary_overlay) {
        title += " (" + trans("PRIMARY_OVERLAY") + ")";
      }
      if (!item.exists) {
        className += " alt-missing";
      }

      const path = pathToAdminPage(
        this.props.match.params.page,
        getUrlRecordPathWithAlt(this.props.record.path, item.alt)
      );
      return (
        <li key={item.alt} className={className}>
          <Link to={path}>{title}</Link>
        </li>
      );
    });

    return (
      <div className="section">
        <h3>{trans("ALTS")}</h3>
        <ul className="nav">{items}</ul>
      </div>
    );
  }
}
