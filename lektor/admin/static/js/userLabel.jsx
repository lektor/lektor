'use strict'

import React from 'react'
import i18n from './i18n'

const userLabel = {

  // formats a user label appropriately
  format(inputConfig) {
    let label = null;
    if (typeof inputConfig === 'string') {
      label = inputConfig;
    } else {
      label = i18n.trans(inputConfig);
    }
    if (!label) {
      return <span className=""></span>;
    }

    let iconData = label.match(/^\[\[\s*(.*?)\s*(;\s*(.*?))?\s*\]\]$/);
    if (iconData) {
      let className = 'fa fa-' + iconData[1];
      if ((iconData[3] || '').match(/90|180|270/)) {
        className += ' fa-rotate-' + iconData[3];
      }
      return <i className={className}></i>
    }

    return <span>{label}</span>;
  }
};


export default userLabel
