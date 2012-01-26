

/* Credits:
*** Andi Smith, Using jQuery .on() and .off()
  * http://www.andismith.com/blog/2011/11/on-and-off/
*** Queness, Simple jQuery Modal Window Tutorial
  * http://www.queness.com/post/77/simple-jquery-modal-window-tutorial
*/


jQuery(document).ready( function($) {

	$.mobile.ajaxEnabled=false
	/**********************/
	/*** CALENDAR VIEWS ***/
	/**********************/	

	function showCalendar() {
		$('.feed-items').fadeOut(300);
		$('.calendar-toggled').delay(300).fadeIn(300);
		$('#showCalendar').text('Back to Feed View').attr('id', 'hideCalendar');
		return false;
	}

	function hideCalendar() {
		$('.calendar-toggled').fadeOut(300);
		$('.feed-items').delay(300).fadeIn(300);
		$('#hideCalendar').text('Switch to Calendar View').attr('id', 'showCalendar');	
		return false;
	}

	function swapCalendarViews() {
		var calendarViews = {
			'#dailyView' : 'daily-event',
			'#weeklyView' : 'weekly-day',
			'#monthlyView' : 'monthly-day'
		};

		$.each(calendarViews, function(key, value) {	
			$(key).click( function() {
				//$('.calendar').fadeOut(200);
				$('.calendar li').removeClass()
				.addClass(value);
				//$('.calendar').delay(200).fadeIn(200);
				$('.calendar-view-title').text('text');
				$('#calendarViews li').removeClass('selected-menu-item');
				$(this).addClass('selected-menu-item');
			});
		});		
	}
	
	// Attach functions when target is on the page
	$('.main').on('click', '#showCalendar', showCalendar)
			  .on('click', '#hideCalendar', hideCalendar)
			  .on('click', '#calendarViews li', swapCalendarViews);
	


	/********************/
	/*** MODAL WINDOW ***/
	/********************/
	
	function openGrabbitModal(e) {
		e.preventDefault();

		var id = $(this).attr('href');

		var maskHeight = $(document).height();
		var maskWidth = $(document).width(); 

		$('#modalMask').css({ 'width':maskWidth, 'height':maskHeight })
					   .fadeTo('slow', 0.5);
		
		var winHeight = $(window).height();
		var winWidth = $(window).width();

		var modalTop = maskHeight/2-$(id).height()/2;
		var modalLeft = maskWidth/2-$(id).width()/2;

		$(id).css({ 'top':modalTop, 'left':modalLeft });

		$(id).fadeIn(500);
	}

	function hideGrabbitModal() {
		$(this).fadeOut(200);
		$('.window').fadeOut(100);
	}

	$('.main').on('click', 'a[name=modal]', openGrabbitModal)
			  .on('click', '#modalMask', hideGrabbitModal);


	/******************/
	/*** ANIMATIONS ***/
	/******************/
	
		
}); // document.ready



/*****************/
/*** BASIC MAP ***/
/*****************/


/*function initializeMap() {

	var latlng = new google.maps.LatLng(40.381423,-80.222168);
	var myOptions = {
		zoom: 12,
		center: latlng,
		mapTypeId: google.maps.MapTypeId.ROADMAP
	};

	var map = new google.maps.Map(document.getElementById('map_canvas'), myOptions);
}*/


