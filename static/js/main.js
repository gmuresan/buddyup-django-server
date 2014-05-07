$("#scroll").click(function() {
  $('html, body').animate({
    scrollTop: $('#first-section').position().top}, 800);
});