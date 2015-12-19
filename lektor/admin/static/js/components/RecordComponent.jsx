'use strict';

var React = require('react');
var Router = require('react-router');

var Component = require('./Component');
var utils = require('../utils');


/* a react component baseclass that has some basic knowledge about
   the record it works with. */
class RecordComponent extends Component {

  /* checks if the record preview is active. */
  isRecordPreviewActive() {
    var routes = this.props.routes;
    return (
      routes.length > 0 &&
      routes[routes.length - 1].component.name === 'PreviewPage'
    );
  }

  /* this returns the current record path segments as array */
  getRecordPathSegments() {
    var path = this.props.params.path;
    return path ? utils.urlPathToSegments(path) : [];
  }

  _getRecordPathAndAlt() {
    var path = this.props.params.path;
    if (!path) {
      return [null, null];
    }
    var items = path.split(/\+/, 2);
    return [utils.urlToFsPath(items[0]), items[1]];
  }

  /* this returns the path of the current record.  If the current page does
   * not have a path component then null is returned. */
  getRecordPath() {
    var [path, _] = this._getRecordPathAndAlt();
    return path;
  }

  /* returns the current alt */
  getRecordAlt() {
    var [_, alt] = this._getRecordPathAndAlt();
    return !alt ? '_primary' : alt;
  }

  /* return the url path for the current record path (or a modified one)
     by preserving or overriding the alt */
  getUrlRecordPathWithAlt(newPath, newAlt) {
    if (newPath === undefined || newPath === null) {
      newPath = this.getRecordPath();
    }
    if (newAlt === undefined || newAlt === null) {
      newAlt = this.getRecordAlt();
    }
    var rv = utils.fsToUrlPath(newPath);
    if (newAlt !== '_primary') {
      rv += '+' + newAlt;
    }
    return rv;
  }

  /* returns the parent path if available */
  getParentRecordPath() {
    return utils.getParentFsPath(this.getRecordPath());
  }

  /* returns true if this is the root record */
  isRootRecord() {
    return this.getRecordPath() === '';
  }

  /* returns the breadcrumbs for the current record path */
  getRecordCrumbs() {
    var segments = this.getRecordPathSegments();
    if (segments === null) {
      return [];
    }

    segments.unshift('root');

    var rv = [];
    for (var i = 0; i < segments.length; i++) {
      var curpath = segments.slice(0, i + 1).join(':');
      rv.push({
        id: 'path:' + curpath,
        urlPath: curpath,
        segments: segments.slice(1, i + 1),
        title: segments[i]
      });
    }

    return rv;
  }
}

module.exports = RecordComponent;
