// from https://github.com/whitequark/ipaddr.js
const ipv6Part = '(?:[0-9a-f]+::?)+';
const ipv4Part = '(0?\\d+|0x[a-f0-9]+)';
const ipv6Regexes = {
  'native': new RegExp(`^(::)?(${ipv6Part})?([0-9a-f]+)?(::)?$`, 'i'),
  transitional: new RegExp(`^((?:${ipv6Part})|(?:::)(?:${ipv6Part})?)${ipv4Part}\\.${ipv4Part}\\.${ipv4Part}\\.${ipv4Part}$`, 'i')
};

function expandIPv6(string, parts) {
  var colonCount, lastColon, part, replacement, replacementCount;
  if (string.indexOf('::') !== string.lastIndexOf('::')) {
    return null;
  }
  colonCount = 0;
  lastColon = -1;
  while ((lastColon = string.indexOf(':', lastColon + 1)) >= 0) {
    colonCount++;
  }
  if (string.substr(0, 2) === '::') {
    colonCount--;
  }
  if (string.substr(-2, 2) === '::') {
    colonCount--;
  }
  if (colonCount > parts) {
    return null;
  }
  replacementCount = parts - colonCount;
  replacement = ':';
  while (replacementCount--) {
    replacement += '0:';
  }
  string = string.replace('::', replacement);
  if (string[0] === ':') {
    string = string.slice(1);
  }
  if (string[string.length - 1] === ':') {
    string = string.slice(0, -1);
  }
  return (function () {
    var i, len, ref, results;
    ref = string.split(':');
    results = [];
    for (i = 0, len = ref.length; i < len; i++) {
      part = ref[i];
      results.push(parseInt(part, 16));
    }
    return results;
  })();
}

function padToFour(number) {
  return number <= 9999 ? ('000' + number.toString(16)).slice(-4) : number.toString(16);
}

function toFullAddress(addr) {
  return addr.map(i => {
    return padToFour(i);
  });
}

export default function parse(string) {
  var match, parts;
  if (string.match(ipv6Regexes['native'])) {
    return toFullAddress(expandIPv6(string, 8));
  } else if ((match = string.match(ipv6Regexes['transitional']))) {
    parts = expandIPv6(match[1].slice(0, -1), 6);
    if (parts) {
      parts.push(parseInt(match[2]) << 8 | parseInt(match[3]));
      parts.push(parseInt(match[4]) << 8 | parseInt(match[5]));
      return toFullAddress(parts);
    }
  }
  return null;
}
