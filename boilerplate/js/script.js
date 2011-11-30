/* Author:

*/


$(document).ready(function(){
	
	// Run Matt Kersley's jQuery Responsive menu plugin (see plugins.js)
	if ($.fn.mobileMenu) {
		$('ol#id').mobileMenu({
			switchWidth: 768,                   // width (in px to switch at)
			topOptionText: 'Choose a page',     // first option text
			indentString: '&nbsp;&nbsp;&nbsp;'  // string for indenting nested items
		});
	}

	// Run Mathias Bynens jQuery placeholder plugin (see plugins.js)
	if ($.fn.placeholder) {
		$('input, textarea').placeholder();		
	}


	initializeMap();
	
	// **** Lara's **** //	
			
	// Will use this to detect media queries with Modernizr:
	// if (Modernizr.mq('only all and (min-width: 800px)')) { ... }


	// Toggle main accordion panels
	/*$('.main-panel-head').click(function(){
		$(this).next('div').slideToggle();
	});*/

	$('.logo').hide().delay(200).show('slide', {direction: 'right'}, 500);;

	//$('.logo').slideDown(500);


	// Expand the add filter form 
	$('.filter-form').hide();
	$('.expand-option.filter').click(function(){
		$('.filter-form').slideDown(400);
	});


	$('.additional-indo').hide();
	$('#showUserStats').hover( function(){
		$('.additional-info').fadeIn(350);
	}, function(){
		$('.additional-info').fadeOut(500);
	});
	



	//**
	//** Map and Chatter box toggle animations 
	//**

	// http://return-true.com/2010/02/jquery-snippet-slideout-tab/
	// http://forum.jquery.com/topic/jquery-animate-percentage
	// http://www.learningjquery.com/2009/02/slide-elements-in-different-directions

	$('.hide-show#map').toggle(function() {
		$('.map-container').animate({ width:($('.map-container').width()*0) }, 500);
		$('.nat-container').animate({ width:($('.nat-container').width()*2.7) }, 500);
		$('.sidebar-tabs').addClass('expanded');
		$('.sidebar-tabs').removeClass('collapsed');
		$('.arrow-collapse').removeClass('left');
		$('.arrow-collapse').addClass('right');
	}, function() {
		$('.nat-container').animate({width:($('.nat-container').width()/3.5)}, { duration: 500 });
		$('.map-container').animate({ width:($('.nat-container').width()/1.4) },500);
		$('.sidebar-tabs').removeClass('expanded');
		$('.sidebar-tabs').addClass('collapsed');
		$('.arrow-collapse').removeClass('right');
		$('.arrow-collapse').addClass('left');
	});
	
	/*$('.hide-show#chatterbox').click(function() {
		$('.first').toggle('slow', { left: '-1000px' });
	});*/


	// http://www.learningjquery.com/2009/02/slide-elements-in-different-directions
	$('button#pageSlideLeft').click(function() {
		var $lefty = $('.content');
		$lefty.animate({
		left: parseInt($lefty.css('left'),10) == 0 ?
			-$lefty.outerWidth() :
			0
		});
	});


	// **** jQuery UI (altered from demo) **** //

	// Tabs
	$('.sidebar-tabs').tabs();
	$('.sidebar-nav > ul').removeClass('ui-widget-header');

	// Shouldn't need to specify selected
	// But it was defaulting to 1, so I did
	$('.chatter-tabs').tabs({ selected: 0 }).removeClass('ui-widget-content ui-corner-all');
	//$('.chatter-tabs > ul').removeClass('ui-widget-header ui-corner-all');

	// Button
	$('button').button().removeClass('ui-button ui-button-text-only');

	// Dialog			
	$('.more-info').dialog({
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
	$('.more-info-link').click(function(){
		$('.more-info').dialog('open');
		return false;
	});

	// Datepicker 
	/* $('#datepicker').datepicker({
		inline: true
	});
	
	// Slider
	$('#slider').slider({
		range: true,
		values: [17, 67]
	}); */
	
	// Progressbar 
	$(".progressbar").progressbar({
		value: 20 // Retrieve value from db here
	});
	
	//hover states on the static widgets
	/* $('#dialog_link, ul#icons li').hover(
		function() { $(this).addClass('ui-state-hover'); }, 
		function() { $(this).removeClass('ui-state-hover'); }
	);*/
	
});

/////////
// MAP //
/////////

function initializeMap() {	
		
	// Your location will be the center of the map	
	var youLoc = new google.maps.LatLng(40.43616876605956, -79.99231338500977);

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
