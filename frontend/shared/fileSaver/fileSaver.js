const dependencies = [];

export default angular.module('boss.fileSaver', dependencies)
  .factory('fileSaver', function () {
    return {
      createForm: function createForm(httpConfig) {
        var fakeForm = `<form style="display: none;" method="${httpConfig.method}" action="${httpConfig.url}">`;
        Object.keys(httpConfig.data).forEach(key => {
          fakeForm += `<input type="hidden" name="${key}" value="${httpConfig.data[key]}">`;
        });
        fakeForm += '</form>';
        return $(fakeForm);
      },
      saveFileFromHttp: function saveFileFromHttp(httpConfig) {
        var $fakeFormDom = this.createForm(httpConfig);
        $('body').append($fakeFormDom);
        $fakeFormDom.submit().remove();
      }
    };
  });
