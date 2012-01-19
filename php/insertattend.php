<?php  

require_once('etc/config.php');
// Get parameters from URL
$userid = $_GET["userid"];
$eventid = $_GET["eventid"];


// Opens a connection to a mySQL server
$connection = mysql_connect(EVENTS_DB_HOST, EVENTS_DB_USER, EVENTS_DB_PASSWORD);
if (!$connection) {
  die("Not connected : " . mysql_error());
}

// Set the active mySQL database
$db_selected = mysql_select_db(EVENTS_DB_NAME, $connection);
if (!$db_selected) {
  die ("Can\'t use db : " . mysql_error());
}

// Search the rows in the markers table
$query = sprintf("INSERT INTO events_hackattendance (event_id, user_id) VALUES ('%s', '%s')", 
  mysql_real_escape_string($eventid),
  mysql_real_escape_string($userid));
$result = mysql_query($query);

if (!$result) {
  die("Invalid query: " . mysql_error());
}

$output_json= array('status' => 'success');

header("Content-type: application/json");
print json_encode($output_json);