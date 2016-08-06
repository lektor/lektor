'use strict'

import React from 'react'
import utils from '../utils'
import i18n from '../i18n'
import hub from '../hub'
import {AttachmentsChangedEvent} from '../events'
import RecordComponent from './RecordComponent'
import Link from '../components/Link'


function getBrowseButtonTitle() {
  const platform = utils.getPlatform();
  if (platform === 'mac') {
    return i18n.trans('BROWSE_FS_MAC');
  } else if (platform === 'windows') {
    return i18n.trans('BROWSE_FS_WINDOWS');
  } else {
    return i18n.trans('BROWSE_FS');
  }
}


const CHILDREN_PER_PAGE = 15;


class ChildPosCache {

  constructor() {
    this.memo = [];
  }

  rememberPosition(record, page) {
    for (let i = 0; i < this.memo.length; i++) {
      if (this.memo[i][0] === record) {
        this.memo[i][1] = page;
        return;
      }
    }
    this.memo.unshift([record, page]);
    if (this.memo.length > 5) {
      this.memo.length = 5;
    }
  }

  getPosition(record, childCount) {
    for (let i = 0; i < this.memo.length; i++) {
      if (this.memo[i][0] === record) {
        let rv = this.memo[i][1];
        if (childCount !== undefined) {
          rv = Math.min(rv, Math.ceil(childCount / CHILDREN_PER_PAGE));
        }
        return rv;
      }
    }
    return 1;
  }
}


class Sidebar extends RecordComponent {

  constructor(props) {
    super(props);

    this.state = this._getInitialState();
    this.childPosCache = new ChildPosCache();
    this.onAttachmentsChanged = this.onAttachmentsChanged.bind(this);
  }

  _getInitialState() {
    return {
      recordAttachments: [],
      recordChildren: [],
      recordAlts: [],
      canHaveAttachments: false,
      canHaveChildren: false,
      isAttachment: false,
      canBeDeleted: false,
      recordExists: false,
      lastRecordRequest: null,
      childrenPage: 1
    };
  }

  componentDidMount() {
    super.componentDidMount();
    this._updateRecordInfo();

    hub.subscribe(AttachmentsChangedEvent, this.onAttachmentsChanged);
  }

  componentDidUpdate(prevProps, prevState) {
    super.componentDidUpdate(prevProps, prevState);
    if (prevProps.params.path !== this.props.params.path) {
      this._updateRecordInfo();
    }
  }

  componentWillUnmount() {
    super.componentWillUnmount();
    hub.unsubscribe(AttachmentsChangedEvent, this.onAttachmentsChanged);
  }

  onAttachmentsChanged(event) {
    if (event.recordPath === this.getRecordPath()) {
      this._updateRecordInfo();
    }
  }

  _updateRecordInfo() {
    const path = this.getRecordPath();
    if (path === null) {
      this.setState(this._getInitialState());
      return;
    }

    this.setState({
      lastRecordRequest: path,
    }, () => {
      utils.loadData('/recordinfo', {path: path})
        .then((resp) => {
          // we're already fetching something else.
          if (path !== this.state.lastRecordRequest) {
            return;
          }
          const alts = resp.alts;
          alts.sort((a, b) => {
            const nameA = (a.is_primary ? 'A' : 'B') + i18n.trans(a.name_i18n);
            const nameB = (b.is_primary ? 'A' : 'B') + i18n.trans(b.name_i18n);
            return nameA === nameB ? 0 : nameA < nameB ? -1 : 1;
          });
          this.setState({
            recordAttachments: resp.attachments,
            recordChildren: resp.children,
            recordAlts: alts,
            canHaveAttachments: resp.can_have_attachments,
            canHaveChildren: resp.can_have_children,
            isAttachment: resp.is_attachment,
            canBeDeleted: resp.can_be_deleted,
            recordExists: resp.exists,
            childrenPage: this.childPosCache.getPosition(
              path, resp.children.length),
          });
        });
    });
  }

  fsOpen(event) {
    event.preventDefault();
    utils.apiRequest('/browsefs', {data: {
      path: this.getRecordPath(),
      alt: this.getRecordAlt()
    }, method: 'POST'})
      .then((resp) => {
        if (!resp.okay) {
          alert(i18n.trans('ERROR_CANNOT_BROWSE_FS'));
        }
      });
  }

  renderPageActions() {
    const urlPath = this.getUrlRecordPathWithAlt();
    const links = [];
    const linkParams = {path: urlPath};
    const deleteLink = null;

    links.push(
      <li key='edit'>
        <Link to={`${urlPath}/edit`}>
          {this.state.isAttachment ?
           i18n.trans('EDIT_METADATA') :
           i18n.trans('EDIT')}
         </Link>
       </li>
    );

    if (this.state.canBeDeleted) {
      links.push(
        <li key='delete'><Link to={`${urlPath}/delete`}>
          {i18n.trans('DELETE')}</Link></li>
      );
    }

    links.push(
      <li key='preview'><Link to={`${urlPath}/preview`}>
        {i18n.trans('PREVIEW')}</Link></li>
    );

    if (this.state.recordExists) {
      links.push(
        <li key='fs-open'>
          <a href="#" onClick={this.fsOpen.bind(this)}>
            {getBrowseButtonTitle()}
          </a>
        </li>
      );
    }

    if (this.state.canHaveChildren) {
      links.push(
        <li key='add-child'><Link to={`${urlPath}/add-child`}>
          {i18n.trans('ADD_CHILD_PAGE')}</Link></li>
      );
    }

    if (this.state.canHaveAttachments) {
      links.push(
        <li key='add-attachment'><Link to={`${urlPath}/upload`}>
          {i18n.trans('ADD_ATTACHMENT')}</Link></li>
      );
    }

    const title = this.state.isAttachment
      ? i18n.trans('ATTACHMENT_ACTIONS')
      : i18n.trans('PAGE_ACTIONS');

    return (
      <div key="actions" className="section">
        <h3>{title}</h3>
        <ul className="nav">
          {links}
          {deleteLink}
        </ul>
      </div>
    );
  }

  renderAlts() {
    if (this.state.recordAlts.length < 2) {
      return null;
    }

    const alt = this.getRecordAlt();

    const items = this.state.recordAlts.map((item) => {
      let title = i18n.trans(item.name_i18n);
      let className = 'alt';
      if (item.is_primary) {
        title += ' (' + i18n.trans('PRIMARY_ALT') + ')';
      } else if (item.primary_overlay) {
        title += ' (' + i18n.trans('PRIMARY_OVERLAY') + ')';
      }
      if (!item.exists) {
        className += ' alt-missing';
      }

      const path = this.getPathToAdminPage(null, {
        path: this.getUrlRecordPathWithAlt(null, item.alt)
      });
      return (
        <li key={item.alt} className={className}>
          <Link to={path}>{title}</Link>
        </li>
      );
    });

    return (
      <div key="alts" className="section">
        <h3>{i18n.trans('ALTS')}</h3>
        <ul className="nav">
          {items}
        </ul>
      </div>
    );
  }

  renderChildPagination() {
    let pages = Math.ceil(this.state.recordChildren.length / CHILDREN_PER_PAGE);
    if (pages <= 1) {
      return null;
    }
    let page = this.state.childrenPage;
    let goToPage = (diff, event) => {
      event.preventDefault();
      let newPage = page +diff;
      this.childPosCache.rememberPosition(this.getRecordPath(), newPage);
      this.setState({
        childrenPage: newPage
      });
    };

    return (
      <li className="pagination">
        {page > 1
          ? <a href="#" onClick={goToPage.bind(this, -1)}>«</a>
          : <em>«</em>}
        <span className="page">{page + ' / ' + pages}</span>
        {page < pages
          ? <a href="#" onClick={goToPage.bind(this, +1)}>»</a>
          : <em>»</em>}
      </li>
    );
  }

  renderChildActions() {
    const target = this.isRecordPreviewActive() ? 'preview' : 'edit';

    const children = this.state.recordChildren.slice(
      (this.state.childrenPage - 1) * CHILDREN_PER_PAGE,
      this.state.childrenPage * CHILDREN_PER_PAGE);

    const items = children.map((child) => {
      const urlPath = this.getUrlRecordPathWithAlt(child.path);
      return (
        <li key={child.id}>
          <Link to={`${urlPath}/${target}`}>
            {i18n.trans(child.label_i18n)}</Link>
        </li>
      )
    });

    if (items.length == 0) {
      items.push(
        <li key="_missing">
          <em>{i18n.trans('NO_CHILD_PAGES')}</em>
        </li>
      );
    }

    return (
      <div key="children" className="section">
        <h3>{i18n.trans('CHILD_PAGES')}</h3>
        <ul className="nav record-children">
          {this.renderChildPagination()}
          {items}
        </ul>
      </div>
    );
  }

  renderAttachmentActions() {
    const items = this.state.recordAttachments.map((atch) => {
      const urlPath = this.getUrlRecordPathWithAlt(atch.path);
      return (
        <li key={atch.id}>
          <Link to={`${urlPath}/edit`}>
            {atch.id} ({atch.type})</Link>
        </li>
      )
    });

    if (items.length == 0) {
      items.push(
        <li key="_missing">
          <em>{i18n.trans('NO_ATTACHMENTS')}</em>
        </li>
      );
    }

    return (
      <div key="attachments" className="section">
        <h3>{i18n.trans('ATTACHMENTS')}</h3>
        <ul className="nav record-attachments">
          {items}
        </ul>
      </div>
    );
  }

  render() {
    const sections = [];

    if (this.getRecordPath() !== null) {
      sections.push(this.renderPageActions());
    }

    sections.push(this.renderAlts());

    if (this.state.canHaveChildren) {
      sections.push(this.renderChildActions());
    }

    if (this.state.canHaveAttachments) {
      sections.push(this.renderAttachmentActions());
    }

    return <div className="sidebar-wrapper">{sections}</div>;
  }
}

export default Sidebar
