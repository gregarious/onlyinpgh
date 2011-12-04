
$(document).ready(function() {
	

	// Sliding Navigation

	// Credit: Queness, "Create a Vertical, Horizontal and Diagonal Sliding Content Website with jQuery"
	// http://www.queness.com/post/356/create-a-vertical-horizontal-and-diagonal-sliding-content-website-with-jquery


	$('#wrapper').scrollTo('#atAGlanceTile', 0);

	$('a.panel').click(function() {
		
		$('a.panel').removeClass('selected');
		$(this).addClass('selected');

		current = $(this);

		$('#wrapper').scrollTo($(this).attr('href'), 800);
		return false;
	});

	$(window).resize(function() {
		resizePanel();
	})
	
	// End slide nav
	
	// Expand scenes-nav on rollover
	$('.dropdown-title#scenesMenu').toggle(function() {
			$('.scenes-nav').fadeIn(500);
			$(this).html('Your Scenes &uarr;');
		}, function() {
			$('.scenes-nav').fadeOut(500);		
			$(this).html('Your Scenes &darr;');
		}
	);	
});

function resizePanel() {
	width = $(window).width;
	height = $(window).height();
	mask_width = width + $('.item').length;

	$('#wrapper, .item').css({width: width, height: height});
	$('#mask').css({width: mask_width, height: height});
	$('#wrapper').scrollTo($('a.selected').attr('href'), 0);
}