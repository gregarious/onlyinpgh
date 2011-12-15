<?php  

class EventSearcher {
	public function __construct($process_output=TRUE) {
		$this->DAYTIME_CUTOFF = '08:00';	// anytime before 4am is considered part of the previous day (for now using 8 AM for utc)
		$this->timezone = date_default_timezone_get();

		$this->q_loc = FALSE;
		$this->q_org = FALSE;
		$this->q_att = FALSE;	

		$this->f_dist = NULL;	// will be 3-tuple of (lat,long,rad) if set
		$this->f_hasgeocode = NULL;	// will be TRUE if set
		$this->f_eid = NULL;	// will be simple event id string if set
		$this->f_sdate = NULL;	// will be date string (no time) if set
		$this->f_edate = NULL;	// will be date string (no time) if set
		$this->f_att = NULL;	// will be user id string if set
		$this->f_kw = NULL;		// will be an array of keywords if set

		$this->query_uid = NULL; // will be a user id if q_att/f_att is set
		
		$this->more_results_exist = FALSE;

		$this->query_args = array();

		$this->process_output = $process_output == TRUE;
	}

	public function queryLocation() {
		$this->q_loc = TRUE;
	}
	public function queryOrganization() {
		$this->q_org = TRUE;	
	}

	// if filterByAttendance has already been called with a userid, it can be omitted
	public function queryAttendance($userid=NULL) {
		$this->q_att = TRUE;
		$this->query_uid = $userid;
	}

	public function setTimezone($timezone_str) {
		$this->timezone = $timezone_str;
	}

	public function filterByDistance($lat,$long,$radius) {
		$this->f_dist = array($lat,$long,$radius);
	}

	public function filterByHasGeocoded() {
		$this->f_hasgeocode = TRUE;
	}

	public function filterByEventId($eid) {
		$this->f_eid = $eid;
	}

	// Must be in YYYY-MM-DD format
	public function filterByStartDate($date) {
		$this->f_sdate = $date;
	}

	// Must be in YYYY-MM-DD format
	public function filterByEndDate($date) {
		$this->f_edate = $date;	
	}

	// if queryAttendance has already been called with a userid, it can be omitted
	public function filterByAttendance($userid=NULL) {
		if($userid!==NULL) {
			$this->query_uid = $userid;	// just ensure genereal WHERE and bookings WHERE clauses match on ID
		}
		$this->f_att = $this->query_uid;
	}

	public function filterByKeyword($kw) {
		$this->filterByKeywords(array($kw));
	}
	public function filterByKeywords($kw_array) {
		$this->f_kw = $kw_array;
	}


/* QUERY BUILDING 

	There are two basic kinds of queries: One with all event info in entire 
	DB, and one with a specified center point. Either of these queries can be
	made more selective by adding the following filters:
	- startdate and/or enddate
	- keyword search
	- offset and/or limit (default limit is 100)

	The query will be built piecemeal in different variables as follows:
	1. the SELECT statement with the optional distance calculation
	2. the optional LEFT JOIN with the bookings table for logged-in "Count me in" status
	3. static clauses for FROM, WHERE, and ORDER BY
	4. a HAVING clause built using only the search criteia provided
	5. a LIMIT clause to limit the results as specified by the caller, or a
			default setting of "LIMIT 0,100"

	Also, an array of values to bind to the PDO query will be built in 
	$query_args when the option's text is added to a clause.
*/

	// returns array of event dicts
	public function runQuery($offset=NULL,$limit=20) {
		$offset = intval($offset);
		$limit = intval($limit);	
		 
		$query = $this->buildSelect() . ' ' .
					$this->buildFrom() . ' ' .
					$this->buildWhere() . ' ' .
					"GROUP BY e.id" . ' ' .
					$this->buildHaving() . ' ' .
					'ORDER BY e.dtend ASC, e.dtstart DESC' . ' ' .
			 		"LIMIT $offset, " . ($limit+1);
		 
		 // connect to DB and run query
		try {
			$pdo = new PDO('mysql:host='.EVENTS_DB_HOST.';dbname='.EVENTS_DB_NAME, 
							EVENTS_DB_USER, EVENTS_DB_PASSWORD);
			$pdo->setAttribute( PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION );
			$statement = $pdo->prepare($query);
			$statement->execute($this->query_args);
			$statement->setFetchMode(PDO::FETCH_ASSOC);
		}
		catch(PDOException $e) {  
		    die('PDO MySQL error: ' . $e->getMessage());  
		} 

		$all_events = array();
		$counter = 0;
		$utc_tz = new DateTimeZone('UTC');
		$local_tz = new DateTimeZone($this->timezone);
		while($row = $statement->fetch()) {
			$counter++;
			if($counter > $limit) break;
			
			// do time zone conversion here
			$dtstart = new DateTime($row['dtstart'],$utc_tz);
			$dtstart->setTimezone($local_tz);
			$dtend = new DateTime($row['dtend'],$utc_tz);
			$dtend->setTimezone($local_tz);

			$new_event =
				array(	'id'			=> intval($row['id']),
						'name'			=> $row['name'],
						'description_short' => $row['description_short'],
						'description'   => $row['description'],
						'categories'	=> ($row['categories'] !== NULL) ?
												explode(',',$row['categories']) : NULL,
						'image_url'		=> $row['image_url'],
						'start_dt'		=> $dtstart,
						'end_dt'		=> $dtend );

			if($this->q_att) {
				$new_event['attending'] = $row['individual']!==NULL;
			}

			if($this->q_loc) {
				$new_event['address'] = $row['address'];
				$new_event['lat'] = $row['latitude'];
				$new_event['long'] = $row['longitude'];
			}

			if($this->q_org) {
				$new_event['org_name'] = $row['organization_name'];
				$new_event['org_url'] = $row['organization_link_url'];
				$new_event['org_fancount'] = 0;	// this is useless
			}

			$all_events[] = $new_event;
		}

		$this->more_results_exist = ($counter>$limit);
		return $all_events;
	}

	// returns TRUE if more results were available than the current query returned
	public function moreResultsAvailable() {
		return $this->more_results_exist;
	}

	private function buildSelect() {
		$select = "SELECT DISTINCT e.name, 
							e.id, 
							e.description,
							SUBSTRING_INDEX(e.description, ' ', 30) as description_short,
							e.dtstart, 
							e.dtend,
							e.image_url,
							GROUP_CONCAT(m.meta_value) as categories";
							
		if($this->q_org||$this->f_kw!==NULL) {
			$select .= ", i.name AS organization_name, 
							o.url AS organization_link_url";
		}

		if($this->q_loc||$this->f_dist!==NULL||$this->f_hasgeocode!==NULL) {
			$select .= ", l.address, 
							l.latitude, 
							l.longitude";

			if($this->f_dist!==NULL) {
				$select .= ", ( 3959 * acos( cos( radians(:lat) ) * cos( radians( l.latitude ) ) * cos( radians( l.longitude ) - radians(:long) ) + sin( radians(:lat) ) * sin( radians( l.latitude ) ) ) ) AS distance";
				$this->query_args['lat'] = $this->f_dist[0];	
				$this->query_args['long'] = $this->f_dist[1];
			}
		}

		if($this->q_att||$this->f_att!==NULL) {
			$select .= ", a.individual";
		}
		return $select;
	}

	private function buildFrom() {
		// always querying primarily from the events table
		$from = "FROM events_event e";

		// if location is being queried
		if($this->q_loc||$this->f_hasgeocode!==NULL||$this->f_dist!==NULL) {
			$from .= " INNER JOIN places_place p ON (e.place_id = p.id)";
			$from .= " INNER JOIN places_location l ON (p.location_id = l.id)";
		}

		// if attendance information is needed
		if($this->q_att||$this->f_att!==NULL) {
			// if we're actually filtering by attendance, use an INNER JOIN to exclude
			//  rows with no attendance by the user. otherwise, just do a LEFT OUTER
			$join_type = ($this->f_att!==NULL) ? "INNER" : "LEFT OUTER";
			$from .= " " . $join_type . " JOIN events_attendee a ON (e.id = a.event_id)";
		}

		// if organization info is needed
		if($this->q_org||$this->f_kw!==NULL) {
			$from .= " LEFT OUTER JOIN events_role ON (e.id = events_role.event_id AND events_role.role_name = 'creator')";
			$from .= " LEFT OUTER JOIN identity_identity i ON (i.id = events_role.organization_id)";
			$from .= " LEFT OUTER JOIN identity_organization o ON (i.id = o.identity_ptr_id)";
		}

		// ensure event types are always returned
		$from .= " LEFT OUTER JOIN events_meta m ON (e.id = m.event_id AND m.meta_key = 'oldtype')";

		return $from;
	}

	// builds where and having clauses
	private function buildWhere() {
		$where_clauses = array();
		
		// if querying by id
		if($this->f_eid!==NULL) {
			$where_clauses[] = 'e.id = :eid';
			$this->query_args['eid'] = $this->f_eid;
		}

		if($this->f_sdate!==NULL) {
			$where_clauses[] = 'e.dtend > :startdate';
			$dt = new DateTime($this->f_sdate);
			// automatically add the time cutoff
			$this->query_args['startdate'] = $dt->format('Y-m-d') . ' ' . $this->DAYTIME_CUTOFF;
		}

		if($this->f_edate!==NULL) {
			$where_clauses[] = 'e.dtstart < :enddate';
			// if end date is D, we actually want to enclude events that start before the daytime cutoff on the next day
			$dt = new DateTime($this->f_edate);
			$dt->add(new DateInterval('P1D'));	// end time is officially 4:00 AM on 
			// automatically add the time cutoff
			$this->query_args['enddate'] = $dt->format('Y-m-d') . ' ' . $this->DAYTIME_CUTOFF;
		}

		if($this->f_hasgeocode!==NULL) {
			$where_clauses[] = "l.latitude IS NOT NULL AND l.longitude IS NOT NULL";
		}

		if($this->f_att!==NULL) {
			$where_clauses[] = "a.individual = :uid";
			$this->query_args['uid'] = $this->query_uid;
		}

		if(count($where_clauses) > 0)
		{
			$where = "WHERE ((" . implode($where_clauses,") AND (") . "))";
		}
		else {
			$where = 'WHERE 1';
		}

		return $where;
	}

	function buildHaving() {
		$having_clauses = array();

		if($this->f_dist!==NULL) {
			$this->query_args['rad'] = $this->f_dist[2];
			$having_clauses[] = "distance < :rad";
		}

		if($this->f_kw!==NULL) {
			$term_clauses = array();
			$i = 0;
			foreach ($this->f_kw as $term) {
				$term_clauses[] = "organization_name rLIKE :keyword$i OR 
									e.name rLIKE :keyword$i OR 
									categories rLIKE :keyword$i OR 
									e.description rLIKE :keyword$i";
				$this->query_args["keyword$i"] = $term;
				$i++;
			}
			$having_clauses[] = implode(' OR ', $term_clauses);
		}

		if(count($having_clauses) > 0)
		{
			return "HAVING ((" . implode($having_clauses,") AND (") . "))";
		}
		else {
			return '';
		}
	}
}