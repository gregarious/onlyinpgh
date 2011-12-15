<?php

require_once 'etc/config.php';
require_once 'include/eventsearcher.class.php';
require_once 'include/oldeventsearcher.class.php';

if(!function_exists('onSameDay')) {
	function onSameDay($dt1,$dt2) {
		if( $dt1->format('H:i') < '04:01' ) {
			$dt1->sub(new DateInterval('P1D'));
		}
		if( $dt2->format('H:i') < '04:01' ) {
			$dt2->sub(new DateInterval('P1D'));
		}

		return $dt1->format('Y-m-d') == $dt2->format('Y-m-d');
	}
}

if(!array_key_exists('eid',$_GET)) {
	die();
}
$eid = intval($_GET['eid']);

if($eid >= 17000) {
	$searcher = new EventSearcher();

	$searcher->queryLocation();
	$searcher->queryOrganization();
	$searcher->setTimezone('US/Eastern');

	// WP/BP functions -- this means this PHP script won't work without WP calling it
	if( is_user_logged_in() ) {
		$searcher->queryAttendance(bp_loggedin_user_id());
	}

	$searcher->filterByEventId($eid);
	$results = $searcher->runQuery(0,1);
}
else {
	$queryer = new OldEventQuery();

	$queryer->queryLocation();
	$queryer->queryOrganization();
	$queryer->setTimezone('US/Eastern');

	// WP/BP functions -- this means this PHP script won't work without WP calling it
	if( is_user_logged_in() ) {
		$queryer->queryAttendance(bp_loggedin_user_id());
	}

	$results = $queryer->runQuery($eid);
}
