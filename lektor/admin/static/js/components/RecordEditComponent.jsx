'use strict'

import RecordComponent from './RecordComponent'
import i18n from '../i18n'


class RecordEditComponent extends RecordComponent {

  hasPendingChanges() {
    return false;
  }

  routerWillLeave(nextLocation) {
    const rv = super.routerWillLeave(nextLocation);
    if (rv !== undefined) {
      return rv;
    }
    if (this.hasPendingChanges()) {
      return i18n.trans('UNLOAD_ACTIVE_TAB');
    }
  }
}

export default RecordEditComponent
