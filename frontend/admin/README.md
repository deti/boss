# BOSS project directory structure

```sh
-boss
  |- backend
  |- bin
  |- configs
  |- deploy
  |- frontend
  |- tests
```

## BOSS Frontend structure

```sh
-frontend
  |- admin
    |- karma
    |- node_modules
    |- src
      |- app
        |- layouts
        |- main
        app.js
      |- assets
        |- translations
      |- less
      index.html
    |- vendor
    |- common
      |- base
      |- less
```

**admin -**
Admin related functionality

**----admin/karma -**
karma configuration files

**----admin/node_modules -**
3rd party dependencies from package.json (npm install)

**----admin/src -**
main source code specific for the app, index.html is located here

**-----admin/src/app -**
view templates, related js code (controllers, directives and so on), app.js is located here

**-----admin/src/assets -**
fonts, logos, translations

**-----admin/src/less -**
less styles, main.less contains only @import's

**----admin/vendor -**
3rd party dependencies from bower.json (bower install)

**-admin/common -**
common functionality for all admin apps

**--admin/common/base -**
base project configurations and constants

**--admin/common/less -**
base project less styles

# Naming convention

BOSS project frontend developers must use following naming convention rules:
> services - <...>Service (eg. abstractMetadataService)
> directives - bs<...> (eg. bsSideMenu)
> controllers - <...>Ctrl (eg. ProfileCtrl)
> filters - filter<...> in directory and .js file names, <...> - name of filter (eg. App.filter('naturalOrderBy',...))

In gereral, use
> functionNamesLikeThis
> variableNamesLikeThis
> ClassNamesLikeThis
> EnumNamesLikeThis
> methodNamesLikeThis
> CONSTANT_VALUES_LIKE_THIS
> foo.namespaceNamesLikeThis.bar

# Code organization rules

1. Controllers should be as short as possible - try to place non-related logic (fetching, manipulating the data) in a services rather then directly in the controller.
2. Single Responsibility - rather than defining a module (and its dependencies), a controller, and a factory all in the same file, separate each one into their own files.

# Common JavaScript coding style

2. *Comments* - write comments. It is useful to leave information that will be read at a later time by people (possibly yourself) who will need to understand what you have done.
All components should be documented with *JSDoc* comments with the appropriate tags and types.
3. *Variables* - all variables should be declared before used. Use of global variables should be minimized.
Example,
```javascript
var currentEntry, // currently selected table entry
    level,        // indentation level
    size;         // size of table
```

4. *Functions* - All functions should be declared before they are used. There should be no space between the name of a function and the '(' (left parenthesis) of its parameter list.
Example,
```javascript
function outer(c, d) {
    var e = c * d;

    function inner(a, b) {
        return (e * a) + b;
    }

    return inner(0, 1);
}
```
If a function literal is anonymous, there should be one space between the word function and the '(' (left parenthesis).
Example,
```javascript
div.onclick = function (e) {
    return false;
};
```
Use of global functions should be minimized.
5. *if statement* - The if class of statements should have the following form:
Example,
```javascript
if (condition) {
    statements
}
if (condition) {
    statements
} else {
    statements
}
```
6. *Semicolons* - Always use semicolons.


# Build

node and npm should be installed

```sh
cd <project-dir>/frontend/admin
npm install
npm run install
npm run build
```
The last command creates 'bin' folder with compiled and minified admin frontend.

```sh
npm run dev
```
The command places built code inside a `build` folder, start local web server with
livereload and watchers to rebuild app on files changes.

```sh
npm run i18n
```
The command extracts all translations keys for angular translate and place them to admin/src/assets/translations

```sh
npm run test
```
The command runs karma tests


## gulp

```sh
$ gulp compile
```
See 'npm run build'

```sh
$ gulp
```
See 'npm run dev'

```sh
$ gulp i18nextract
```
See 'npm run i18n'
