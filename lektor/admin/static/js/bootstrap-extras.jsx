import $ from 'jquery'

$(document).ready(function () {
  $('[data-toggle=offcanvas]').click(function () {
    const target = $($(this).attr('data-target') || '.block-offcanvas')
    const isActive = target.is('.active')
    target.toggleClass('active', !isActive)
    $(this).toggleClass('active', !isActive)
  })
})
