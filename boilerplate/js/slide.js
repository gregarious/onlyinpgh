
$(document).ready(function() {
	
//	initializeMap();


	// Sliding Navigation

	// Credit: Queness, "Create a Vertical, Horizontal and Diagonal Sliding Content Website with jQuery"
	// http://www.queness.com/post/356/create-a-vertical-horizontal-and-diagonal-sliding-content-website-with-jquery

	$('#wrapper').scrollTo('#atAGlanceTile', 0);

	$('a.panel').click(function(event) {

		$('a.panel').removeClass('selected');
		$(this).addClass('selected');

		$('#wrapper').scrollTo($(this).attr('href'), 800);

		/*var target = $(event.target);

		var p = $('div.item#eventsTile .item-content-container').data('posleft', 150);
		console.log(p.left);

		if( target.is('li.events.active a.panel') ) {
			$('.item#eventsTile .item-content-container').animate({
				left: '-=200'
			}, 1000);
		} else {
			$('.item#eventsTile .item-content-container').animate({
				left: '+=200'
			}, 1000);
		}*/

		return false;

	});

	$(window).resize(function() {
		resizePanel();
	});
	
	// End slide nav
	

	// Expand scenes-nav on rollover
	$('.dropdown-title#scenesMenu').toggle(function() {
			$('.scenes-nav').slideDown(300);
			$(this).html('Scenes &uarr;');
		}, function() {
			$('.scenes-nav').slideUp(300);		
			$(this).html('Scenes &darr;');
		}
	);



	// Chatter tabs
	$('.chatter-category-tabs').tabs();


	// Sliding sandwich board - this no work now??
	$('.arrow-slide.left').click( function() {
		$('.ticker #sandwich-board li').scrollTo($('.ticker #sandwich-board li').next());
	});


	// Not working right now
	// Checkin dialog
	$('.checkin-prompt').dialog({
		autoOpen: false,
		width: 600,
		modal: true,
		buttons: {
			"Ok": function() { 
				$(this).dialog("close"); 
			}, 
			"Cancel": function() { 
				$(this).dialog("close"); 
			} 
		}
	});
	
	// Dialog Link
	$('.checkin-prompt-link').click(function(){
		$('.checkin-prompt').dialog('open');
		return false;
	});


});

function resizePanel() {
	width = $(window).width;
	height = $(window).height();
	mask_width = width + $('.item').length;

	$('#wrapper, .item').css({width: width, height: height});
	$('#mask').css({width: mask_width, height: height});
	$('#wrapper').scrollTo($('a.selected').attr('href'), 0);
}

function initializeMap() {	
		
	// Your location will be the center of the map	
	var youLoc = new google.maps.LatLng(40.44201350, -79.96255210);

	var mapOptions = {
		zoom: 14,
		mapTypeId: google.maps.MapTypeId.ROADMAP,
		center: youLoc
	};

	// Create the map
	map = new google.maps.Map(document.getElementById("map_canvas"),
	   mapOptions);

	// Add a dummy 'Your location' maker
    var youMarker = new google.maps.Marker({
        position: youLoc,
        map: map,
    });
	
} // initializeMap

