var data = require('./targets.json');

var fs = require('fs');
var target = 'dev';

if (process.argv.length > 2) {
  target = process.argv[2];
  if (!data[target]) {
    console.error('There is no target "%s" in targets.json');
  }
}

fs.readFile('./src/index.html', 'utf8', function (e, file) {
  if (e) {
    console.error(e);
    return;
  }
  var targetData = data[target];

  Object.keys(targetData).forEach(function (key) {
    var regex = new RegExp('{{' + key + '}}', 'g');
    file = file.replace(regex, targetData[key]);
  });
  var filename = 'index.' + target + '.html';
  fs.writeFile(filename, file, function (e) {
    if (e) {
      console.error(e);
      return
    }
    console.log('File "%s" was generated fot target "%s"', filename, target);
  });
});
