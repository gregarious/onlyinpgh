<?php  
// stripped down EventSearcher class that allows querying for single old ids
class OldEventQuery {
	public function __construct($process_output=TRUE) {
		$this->DAYTIME_CUTOFF = '08:00';	// anytime before 4am is considered part of the previous day (for now using 8 AM for utc)
		$this->timezone = date_default_timezone_get();

		$this->q_loc = FALSE;
		$this->q_org = FALSE;
		$this->q_att = FALSE;	

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
	}

	public function setTimezone($timezone_str) {
		$this->timezone = $timezone_str;
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
	public function runQuery($eid) {
		$offset = 0;
		$limit = 1;
		 
		$query = $this->buildSelect() . ' ' .
					$this->buildFrom() . ' ' .
					$this->buildWhere($eid) . ' ' .
					"GROUP BY e.id" . ' ' .
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

	private function buildSelect() {
		$select = "SELECT DISTINCT e.name, 
							e.id, 
							e.description,
							SUBSTRING_INDEX(e.description, ' ', 30) as description_short,
							e.dtstart, 
							e.dtend,
							e.image_url,
							GROUP_CONCAT(m.meta_value) as categories";
							
		if($this->q_org) {
			$select .= ", o.name AS organization_name, 
							o.url AS organization_link_url";
		}

		if($this->q_loc) {
			$select .= ", l.address, 
							l.latitude, 
							l.longitude";
		}

		if($this->q_att) {
			$select .= ", a.individual";
		}
		return $select;
	}

	private function buildFrom() {
		// always querying primarily from the events table
		$from = "FROM oldevents_event e";

		// if location is being queried
		if($this->q_loc) {
			$from .= " INNER JOIN oldevents_location l ON (e.location_id = l.id)";
		}

		// if attendance information is needed
		if($this->q_att) {
			// if we're actually filtering by attendance, use an INNER JOIN to exclude
			//  rows with no attendance by the user. otherwise, just do a LEFT OUTER
			$join_type = "LEFT OUTER";
			$from .= " " . $join_type . " JOIN oldevents_attendee a ON (e.id = a.event_id)";
		}

		// if organization info is needed
		if($this->q_org) {
			$from .= " LEFT OUTER JOIN oldevents_role ON (e.id = oldevents_role.event_id AND oldevents_role.role_name = 'creator')";
			$from .= " LEFT OUTER JOIN oldevents_organization o ON (oldevents_role.organization_id = o.id)";
		}

		// ensure event types are always returned
		$from .= " LEFT OUTER JOIN oldevents_meta m ON (e.id = m.event_id AND m.meta_key = 'oldtype')";

		return $from;
	}

	// builds where and having clauses
	private function buildWhere($eid) {
		$where = 'WHERE e.id = :eid';
		$this->query_args['eid'] = $eid;
		return $where;
	}
}