import React from "react";

class Component extends React.Component {
  /**
   * Helper to generate URL path for an admin page.
   * @param {string | null} name - Name of the page (or null for the current one)
   * @param {string} path - Record path
   */
  getPathToAdminPage(name, path) {
    const pageName = name !== null ? name : this.props.match.params.page;
    return `${$LEKTOR_CONFIG.admin_root}/${path}/${pageName}`;
  }

  /**
   * Helper to transition to a specific page
   * @param {string} name - Page name
   * @param {string} path - Record path
   */
  transitionToAdminPage(name, path) {
    const url = this.getPathToAdminPage(name, path);
    this.props.history.push(url);
  }
}

export default Component;
