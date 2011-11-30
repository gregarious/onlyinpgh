$.get('/ajax/places', function(data) { 
    $('#places').html(data); }
);

$.get('/ajax/events', function(data) { 
    $('#events').html(data); }
);

$.get('/ajax/offers', function(data) { 
    $('#sandwich-board').html(data); }
);

$.get('/ajax/news', function(data) { 
    $('#burghosphere').html(data); }
);