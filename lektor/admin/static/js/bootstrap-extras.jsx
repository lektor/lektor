import $ from 'jquery'

$(document).ready(() => {
  $('[data-toggle=offcanvas]').click(() => {
    const target = $($(this).attr('data-target') || '.block-offcanvas')
    const isActive = target.is('.active')
    target.toggleClass('active', !isActive)
    $(this).toggleClass('active', !isActive)
  })
})
