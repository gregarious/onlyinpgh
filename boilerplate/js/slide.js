
$(document).ready(function() {
	
	//initializeMap();


	// Sliding Navigation

	// Credit: Queness, "Create a Vertical, Horizontal and Diagonal Sliding Content Website with jQuery"
	// http://www.queness.com/post/356/create-a-vertical-horizontal-and-diagonal-sliding-content-website-with-jquery

	$('#wrapper').scrollTo('#atAGlanceTile', 0);

	$('a.panel').click(function(event) {

		$('a.panel').removeClass('selected');
		$(this).addClass('selected');

		var target = $(event.target);

		// Could be done more efficiently, but works
		if( target.is('li.events.active a.panel') ) {
			$('#wrapper').scrollTo($(this).attr('href'), 800, { offset:{left:$('.item').width()/6} });
		} else if( target.is('li.chatterbox.active a.panel') ) {
			$('#wrapper').scrollTo($(this).attr('href'), 800, { offset:{left:-$('.item').width()/6} });
		} else {
			$('#wrapper').scrollTo($(this).attr('href'), 800);
		}
		return false;

	});

	$(window).resize(function() {
		resizePanel();
	});
	
	// End slide nav
	

	// Expand scenes-nav on rollover
	$('.dropdown-title#scenesMenu').toggle(function() {
			$('.scenes-nav').slideDown(300);
			$(this).html('More Scenes &uarr;');
		}, function() {
			$('.scenes-nav').slideUp(300);		
			$(this).html('More Scenes &darr;');
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


	// Print filter search box value to a list
	$("#add-filter").click(function() {
		var value = $('#search-box').val();
		$("#current-filters").append('<li><span class="remove-filter"></span>' + value + '</li>');
		// Animation when adding tag - adds a display:block...will have to fix that, so not using now
		/*$('<li><span class="remove-tag pointer"></span>' + value + '</li>')
			.hide()
			.appendTo('#list-tags');
			.show(300);*/
				
		$(".remove-filter").click(function() {
			$(this).parent('li').hide(300, function() {
				$(this).remove();
			});

			return false;
		});
		
    });


}); // document.ready

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
	var myOptions = {
      zoom: 8,
      center: youLoc,
      mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    var map = new google.maps.Map(document.getElementById("map_canvas"),
        myOptions);
	
} // initializeMap

