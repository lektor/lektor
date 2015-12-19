'use strict';

var React = require('react');


function lineIsDashes(line) {
  line = line.match(/^\s*(.*?)\s*$/)[1];
  return line.length >= 3 && line == (new Array(line.length + 1)).join('-');
}

function processBuf(buf) {
  var lines = buf.map(function(line) {
    if (lineIsDashes(line)) {
      line = line.substr(1);
    }
    return line;
  });

  if (lines.length > 0) {
    var lastLine = lines[lines.length - 1];
    if (lastLine.substr(lastLine.length - 1) == '\n') {
      lines[lines.length - 1] = lastLine.substr(0, lastLine.length - 1);
    }
  }

  return lines;
}

function tokenize(lines) {
  var key = null;
  var buf = [];
  var wantNewline = false;
  var rv = [];

  function flushItem() {
    rv.push([key, processBuf(buf)]);
    key = null;
    buf = [];
  }

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].match(/^(.*?)(\r?\n)*$/m)[1] + '\n';

    if (line.match(/^(.*?)\s*$/m)[1] == '---') {
      wantNewline = false;
      if (key !== null) {
        flushItem();
      }
    } else if (key !== null) {
      if (wantNewline) {
        wantNewline = false;
        if (line.match(/^\s*$/)) {
          continue;
        }
      }
      buf.push(line);
    } else {
      var bits = line.split(':');
      if (bits.length >= 2) {
        key = bits.shift().match(/^\s*(.*?)\s*$/m)[1];
        var firstBit = bits.join(':').match(/^[\t ]*(.*?)[\t ]*$/m)[1];
        if (!firstBit.match(/^\s*$/)) {
          buf = [firstBit];
        } else {
          buf = [];
          wantNewline = true;
        }
      }
    }
  }

  if (key !== null) {
    flushItem();
  }

  return rv;
}

function serialize(blocks) {
  var rv = [];

  blocks.forEach(function(item, idx) {
    var [key, value] = item;
    if (idx > 0) {
      rv.push('---\n');
    }
    if (value.match(/([\r\n]|(^[\t ])|([\t ]$))/m)) {
      rv.push(key + ':\n');
      rv.push('\n');
      var lines = value.split(/\n/);
      if (lines[lines.length - 1] === '') {
        lines.pop();
      }
      lines.forEach(function(line, idx, arr) {
        if (lineIsDashes(line)) {
          line = '-' + line;
        }
        rv.push(line + '\n');
      });
    } else {
      rv.push(key + ': ' + value + '\n');
    }
  });

  return rv;
}


module.exports = {
  tokenize: tokenize,
  serialize: serialize
};
