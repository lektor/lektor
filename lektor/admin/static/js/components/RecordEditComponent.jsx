'use strict';

var RecordComponent = require('./RecordComponent');
var i18n = require('../i18n');


class RecordEditComponent extends RecordComponent {

  hasPendingChanges() {
    return false;
  }

  routerWillLeave(nextLocation) {
    var rv = super.routerWillLeave(nextLocation);
    if (rv !== undefined) {
      return rv;
    }
    if (this.hasPendingChanges()) {
      return i18n.trans('UNLOAD_ACTIVE_TAB');
    }
  }
}

module.exports = RecordEditComponent;
