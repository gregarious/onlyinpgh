

/* Credits:
*** Andi Smith, Using jQuery .on() and .off()
  * http://www.andismith.com/blog/2011/11/on-and-off/
*** Queness, Simple jQuery Modal Window Tutorial
  * http://www.queness.com/post/77/simple-jquery-modal-window-tutorial
*/


jQuery(document).ready( function($) {

	$.mobile.ajaxLinksEnabled = false;

	$('#submitSearch').click(function() {
		printSelectedTags();
	});


	function printSelectedTags() {
		$('#tagSearchChoice option').each( function() {
			$('#searchSummary').text($(this).val());
		});
	}
		
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


