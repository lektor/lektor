'use strict';

var React = require('react');

var RecordComponent = require('./RecordComponent');
var Link = require('./Link');
var utils = require('../utils');
var i18n = require('../i18n');
var dialogSystem = require('../dialogSystem');
var FindFiles = require('../dialogs/findFiles');
var Publish = require('../dialogs/publish');
var Refresh = require('../dialogs/Refresh');


class BreadCrumbs extends RecordComponent {

  constructor(props) {
    super(props);
    this.state = {
      recordPathInfo: null,
    };
    this._onKeyPress = this._onKeyPress.bind(this);
  }

  componentDidMount() {
    super.componentDidMount();
    this.updateCrumbs();
    window.addEventListener('keydown', this._onKeyPress);
  }

  componentDidUpdate(prevProps, prevState) {
    super.componentDidUpdate(prevProps, prevState);
    if (prevProps.params.path !== this.props.params.path) {
      this.updateCrumbs();
    }
  }

  componentWillUnmount() {
    window.removeEventListener('keydown', this._onKeyPress);
  }

  updateCrumbs() {
    var path = this.getRecordPath();
    if (path === null) {
      this.setState({
        recordPathInfo: null
      });
      return;
    }

    utils.loadData('/pathinfo', {path: path})
      .then((resp) => {
        this.setState({
          recordPathInfo: {
            path: path,
            segments: resp.segments
          }
        });
      });
  }

  _onKeyPress(event) {
    // meta+g is open find files
    if (event.which == 71 && utils.isMetaKey(event)) {
      event.preventDefault();
      dialogSystem.showDialog(FindFiles);
    }
  }

  _onCloseClick(e) {
    utils.loadData('/previewinfo', {
      path: this.getRecordPath(),
      alt: this.getRecordAlt()
    })
    .then((resp) => {
      if (resp.url === null) {
        window.location.href = utils.getCanonicalUrl('/');
      } else {
        window.location.href = utils.getCanonicalUrl(resp.url);
      }
    });
  }

  _onFindFiles(e) {
    dialogSystem.showDialog(FindFiles);
  }

  _onRefresh(e) {
    dialogSystem.showDialog(Refresh);
  }

  _onPublish(e) {
    dialogSystem.showDialog(Publish);
  }

  renderGlobalActions() {
    return (
      <div className="btn-group">
        <button className="btn btn-default" onClick={
          this._onFindFiles.bind(this)} title={i18n.trans('FIND_FILES')}>
          <i className="fa fa-search fa-fw"></i></button>
        <button className="btn btn-default" onClick={
          this._onPublish.bind(this)} title={i18n.trans('PUBLISH')}>
          <i className="fa fa-cloud-upload fa-fw"></i></button>
        <button className="btn btn-default" onClick={
          this._onRefresh.bind(this)} title={i18n.trans('REFRESH_BUILD')}>
          <i className="fa fa-refresh fa-fw"></i></button>
        <button className="btn btn-default" onClick={
          this._onCloseClick.bind(this)} title={i18n.trans('RETURN_TO_WEBSITE')}>
          <i className="fa fa-eye fa-fw"></i></button>
      </div>
    );
  }

  render() {
    var crumbs = [];
    var target = this.isRecordPreviewActive() ? '.preview' : '.edit';
    var lastItem = null;

    if (this.state.recordPathInfo != null) {
      crumbs = this.state.recordPathInfo.segments.map((item) => {
        var urlPath = this.getUrlRecordPathWithAlt(item.path);
        var label = item.label_i18n ? i18n.trans(item.label_i18n) : item.label;
        var className = 'record-crumb';

        if (!item.exists) {
          label = item.id;
          className += ' missing-record-crumb';
        }
        lastItem = item;

        var adminPath = this.getPathToAdminPage(target, {path: urlPath});

        return (
          <li key={item.path} className={className}>
            <Link to={adminPath}>{label}</Link>
          </li>
        );
      });
    } else {
      crumbs = (
        <li><Link to={this.getPathToAdminPage('.edit', {path: 'root'})}>
          {i18n.trans('BACK_TO_OVERVIEW')}</Link></li>
      )
    }

    return (
      <div className="breadcrumbs">
        <ul className="breadcrumb container">
          {this.props.children}
          {crumbs}
          {lastItem && lastItem.can_have_children ? (
            <li className="new-record-crumb">
              <Link to={this.getPathToAdminPage('.add-child', {
                path: this.getUrlRecordPathWithAlt(
                lastItem.path)})}>+</Link>
            </li>
          ) : null}
          {' ' /* this space is needed for chrome ... */}
          <li className="meta">
            {this.renderGlobalActions()}
          </li>
        </ul>
      </div>
    );
  }
}

module.exports = BreadCrumbs;
