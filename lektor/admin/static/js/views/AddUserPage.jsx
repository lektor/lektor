'use strict';

var React = require('react');
var Router = require('react-router');

var Component = require('../components/Component');
var utils = require('../utils');

class AddUserPage extends Component {
  handleSubmit(e) {
    e.preventDefault();

    var username = e.target.elements['username'].value;
    if (!username) {
      return;
    }

    utils.request('/users/add', {
      json: {username: username},
      method: 'POST'
    }).then((resp) => {
      this.props.history.pushState(
        null, '/admin/users/set-password-link', {username: username, link: resp.link, new_user: true});
    });

  }

  render() {
    return (
      <div>
        <h1>Add a User</h1>
        <form onSubmit={this.handleSubmit.bind(this)}>
          <p>Username <input type="text" name="username"/></p>
          <input type="submit" value="Post" />
        </form>
      </div>
    );
  }
}

module.exports = AddUserPage;
