$(document).ready(function() {
  $('[data-toggle=offcanvas]').click(function() {
    var target = $($(this).attr('data-target') || '.block-offcanvas');
    var isActive = target.is('.active');
    target.toggleClass('active', !isActive);
    $(this).toggleClass('active', !isActive);
  });
});
