var gulp = require('gulp'),
  extractTranslate = require('gulp-angular-translate-extractor');

gulp.task('i18n', function () {
  var i18ndest = './assets/translations';
  return gulp.src([
      '!../shared/skyline/**/*.tpl.html',
      '!../shared/skyline/**/*.js',
      '!../shared/openstackService/**/*.js',
      '../shared/**/*.tpl.html',
      '../shared/**/*.js',
      './src/**/*.tpl.html',
      './src/**/*.js',
      './lib/**/*.tpl.html',
      './lib/**/*.js'
    ])
    .pipe(extractTranslate({
      defaultLang: 'en.i18n',
      lang: ['en.i18n', 'ru.i18n'],
      dest: i18ndest,
      safeMode: false, // do not delete old translations
      stringifyOptions: true // force json to be sorted
    }))
    .pipe(gulp.dest(i18ndest));
});
