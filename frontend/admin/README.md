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
    |- assets
      |- translations
    |- less
    |- lib
    |- node_modules
    |- src
      app.js
      index.html
    |- vendor
```

**admin -**
Admin related functionality

**----admin/assets -**
fonts, logos, translations

**----admin/less -**
less styles, main.less contains only @import's

**----admin/lib -**
common functionality for all admin apps

**----admin/node_modules -**
3rd party dependencies from package.json (npm install)

**----admin/src -**
main source code specific for the app, index.html is located here

**----admin/vendor -**
3rd party dependencies from bower.json (bower install) bower used only for angular-ui-bootstrap, because their npm package
contain only concatinated file

# Build

node and npm should be installed

```sh
cd <project-dir>/frontend/admin
npm install
npm run install
npm run compile
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
