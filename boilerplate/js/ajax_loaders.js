$.get('/ajax/places', function(data) { 
        $('#places').html(data); 
    }
);

$.get('/ajax/events', function(data) { 
        $('#events').html(data); 
    }
);

$.get('/ajax/offers', function(data) { 
        $('#sandwich-board').html(data); 
    }
);

$.get('/ajax/news', function(data) { 
        $('#burghosphere').html(data); 
    }
);

$.get('/ajax/chatter/hot', function(data) { 
        $('#chatter-tab-1').html(data);
    }
);

$.get('/ajax/chatter/new', function(data) { 
        $('#chatter-tab-2').html(data);
    }
);

$.get('/ajax/chatter/photos', function(data) { 
        $('#chatter-tab-3').html(data);
    }
);

$.get('/ajax/chatter/conversations', function(data) { 
        $('#chatter-tab-4').html(data);
    }
);

$.get('/ajax/chatter/questions', function(data) { 
        $('#chatter-tab-5').html(data);
    }
);