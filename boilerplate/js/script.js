

/* Credits:
*** Andi Smith, Using jQuery .on() and .off()
  * http://www.andismith.com/blog/2011/11/on-and-off/
*** Queness, Simple jQuery Modal Window Tutorial
  * http://www.queness.com/post/77/simple-jquery-modal-window-tutorial
*/


jQuery(document).ready( function($) {

	$('#expandSearch').click( function() {
		$('#site-nav').slideToggle(200);
		$('#site-search').slideToggle(200);
	});

	/*$('#submitSearch').click(function() {
		printSelectedTags();
	});

	
	// Make main nav select items links - somewhat a hack, will likely need to change
	$('#select-choice-a').change( function() {

		var menuItem = $(this).attr('value');		
		window.location = "/" + menuItem;

	});


	function printSelectedTags() {
		$('#tagSearchChoice option').each( function() {
			$('#searchSummary').text($(this).val());
		});
	}

	$('#expandQuickSearch').click( function() {
		$('.quick-search').slideToggle(300);
	})
		*/
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


