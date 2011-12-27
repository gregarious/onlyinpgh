

/* Credits:
*** Andi Smith, Using jQuery .on() and .off()
*** http://www.andismith.com/blog/2011/11/on-and-off/
*/

// Reminder for how .on() works:
// $([loaded container selector (probably '.main')])
// .on([action], [ajaxed selector to act on], [handler function]);
// example:
// $('.main').on('click', '.expand-details', handleClick);


jQuery(document).ready( function($) {


	/********************/
	/*** AJAX LOADERS ***/
	/********************/

	// Load single page templates when 
	// associated menu item is clicked

	var menuItems = {
		'#placesMenuItem': '/ajax/places-page', 
		'#eventsMenuItem': '/ajax/events-page',
		'#newsMenuItem': '/ajax/news-page', 
		'#offersMenuItem': '/ajax/offers-page'
	};

	$.each(menuItems, function(key, value) {
			
		$(key).click( function() {

			// Load the new #content; key = the menu item, value = the associated URL
			$.ajax({
				type: 'GET',
				url: value,
				success: function(data, textStatus) {
					$('.main').html(data);
				},
				error: function(xhr, textStatus, errorThrown) {
					alert('an error occurred! ' + errorThrown);
				}
			}); // ajax menu items
			
		}); // key.click
	}); // .each
	

	// This is hacky. 
	// Will need to create a separate template for 
	// home page so it loads in base.html '.main'

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
		});
	
	});
	
	// Load home page feed templates
	// Also a hack, 
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


	/**********************/
	/*** CALENDAR VIEWS ***/
	/**********************/	

	function showCalendar() {
		$('.feed-items').fadeOut(300);
		$('.calendar-toggled').delay(300).fadeIn(300);
	}

	
	function swapCalendarViews() {
		var calendarViews = {
			'#dailyView' : 'daily-event',
			'#weeklyView' : 'weekly-day',
			'#monthlyView' : 'monthly-day'
		};

		$.each(calendarViews, function(key, value) {	
			$(key).click( function() {
				$('.calendar li').removeClass()
				.addClass(value);
				$('.calendar-view-title').text('text');
			});
		});		
	}
	
	$('.main').on('click', '#showCalendar', showCalendar);
	$('.main').on('click', '#calendarViews li', swapCalendarViews);
	

	/******************/
	/*** ANIMATIONS ***/
	/******************/

	
		
}); // document.ready

	/*function expandDetails() {
		$('.page-item-details').hide();
		$('.expand-details').toggle(function () {
			$('.page-item-details').slideToggle();
		});	
	}*/
		