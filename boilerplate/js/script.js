
( function($) {  

	$(document).ready( function() {


		/********************/
		/*** AJAX LOADERS ***/
		/********************/

		// Load single page templates when 
		// associated menu item is clicked

		var menuItems = {
				'#placesMenuItem': '/ajax/places', 
				'#eventsMenuItem': '/ajax/events',
				'#newsMenuItem': '/ajax/news', 
				'#offersMenuItem': '/ajax/offers'
			};

		$.each(menuItems, function(key, value) {
				
			$(key).click(function(){

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
				}); // ajax
				
				// Remove map and current #content children before loading new #content children
				//$('#map').hide(500); // Will be incorporated into #content actions below, not working right now
				//$('#content').children().hide();

			}); // key.click
		}); // .each
		

		// This is a hack. 
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


		/******************/
		/*** ANIMATIONS ***/
		/******************/
		
	});

}) ( jQuery );
	/*function expandDetails() {
		$('.page-item-details').hide();
		$('.expand-details').toggle(function () {
			$('.page-item-details').slideToggle();
		});	
	}*/
		