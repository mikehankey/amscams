$(function() {
    $('.lz').Lazy({
        effect: 'fadeIn',
        visibleOnly: true,
        onError: function(element) {
            console.log('error loading ' + element.data('src'));
        },
        afterLoad: function(element) {
            console.log('LOADED: ' + element.data('src'));
        },
    });
});