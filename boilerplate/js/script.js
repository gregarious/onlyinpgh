

/* Credits:
*** Andi Smith, Using jQuery .on() and .off()
  * http://www.andismith.com/blog/2011/11/on-and-off/
*** Queness, Simple jQuery Modal Window Tutorial
  * http://www.queness.com/post/77/simple-jquery-modal-window-tutorial
*/


// Reminder for how .on() works:
// $([loaded container selector (probably '.main')])
// .on([action], [ajaxed selector to act on], [handler function]);
// example:
// $('.main').on('click', '.expand-details', handleClick);


jQuery(document).ready( function($) {

	//initializeMap();

	/********************/
	/*** AJAX LOADERS ***/
	/********************/

	// Load single page templates when 
	// associated menu item is clicked

	var menuItems = {
		'.places-page-link': '/ajax/places-page', 
		'.events-page-link': '/ajax/events-page',
		'.news-page-link': '/ajax/news-page', 
		'.offers-page-link': '/ajax/offers-page'
	};

	$.each(menuItems, function(key, value) {
			
		$(key).click( function() {

			// Add a loading.gif as well as fade animation here
			$('.main').fadeOut(10);

			// Load the new #content; 
			// key = the menu item, value = the associated URL
			$.ajax({
				type: 'GET',
				url: value,
				success: function(data, textStatus) {
					$('.main').html(data)
							  .fadeIn(300);
				},
				error: function(xhr, textStatus, errorThrown) {
					alert('an error occurred! ' + errorThrown);
				}
			}); // ajax menu items
			
			$('.global-nav li').removeClass('selected-menu-item');
			$(this).addClass('selected-menu-item');

		}); // key.click
	}); // .each
	

	// This is hacky. 
	// Will need to create a separate template for 
	// home page so it loads in base.html '.main'
	// Therefore no fade transition here

	$('#homeMenuItem').click(function () {
		$.ajax({
			type: 'GET',
			url: '/',
			success: function(data, textStatus) {
				$('body').html(data);
			},
			error: function(xhr, textStatus, errorThrown) {
				alert('an error occurred! ' + errorThrown);
			}	
		}); // ajax
	
		$('.global-nav li').removeClass('selected-menu-item');
		$(this).addClass('selected-menu-item');
	
	});
	
	// Load home page feed templates
	// Also hacky, 
	// will change to loading home page template
	// once it exists

	$.get('/ajax/events', function(data) { 
	        $('#eventsFeed').html(data); 
	    }
	);

	$.get('/ajax/offers', function(data) { 
	        $('#offersFeed').html(data); 
	    }
	);

	$.get('/ajax/news', function(data) { 
	        $('#newsFeed').html(data); 
	    }
	);

	function loadSingleEvent() {
		$.get('/ajax/event-single', function(data) { 
				$('.main').html(data); 
	    	}
		);		
		return false;
	}

	function loadSinglePlace() {
		$.get('/ajax/place-single', function(data) { 
				$('.main').html(data); 
	    	}
		);		
		return false;
	}

	$('.main')
		.on('click', '.load-single-event', loadSingleEvent)
		.on('click', '.load-single-place', loadSinglePlace);

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


