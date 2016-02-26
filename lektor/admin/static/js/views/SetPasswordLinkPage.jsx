'use strict';

var React = require('react');
var Router = require('react-router');

var Component = require('../components/Component');
var utils = require('../utils');

class SetPasswordLinkPage extends Component {
  render() {
    var query = this.props.location.query,
        username = query.username,
        link = query.link,
        new_user = JSON.parse(query.new_user);

    if (new_user) {
      return (
        <div>
          <h1>Added user {username}</h1>
          <p>Send {username} a message like the following:</p>
          <blockquote>
            <p>Welcome to the team! You can log in with username <strong>{username}</strong> at the following link:</p>
            <a href={link}>{link}</a>
          </blockquote>
        </div>
      );
    } else {
      return (
        <div>
          <h1>Reset password for user {username}</h1>
          <p>Send {username} a message like the following:</p>
          <blockquote>
            <p>Hey {username}, you can reset your password at the following link:</p>
            <a href={link}>{link}</a>
          </blockquote>
        </div>
      );
    }
  }
}

module.exports = SetPasswordLinkPage;
