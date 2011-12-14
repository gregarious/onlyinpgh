$.get('/ajax/places', function(data) { 
        $('#placesPage').html(data); 
    }
);

$.get('/ajax/places', function(data) { 
        $('#placesFeed').html(data);
    }
);

$.get('/ajax/events', function(data) { 
        $('#events').html(data); 
    }
);

$.get('/ajax/events', function(data) { 
        $('#eventsFeed').html(data);
    }
);

$.get('/ajax/events', function(data) { 
        $('#eventsPage').html(data); 
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

$.get('/ajax/chatter/teaser', function(data) { 
        $('#chatter-teasers').html(data);
    }
);

$.get('/ajax/chatter/hot', function(data) { 
        $('#chatterHottest').html(data);
    }
);

$.get('/ajax/chatter/new', function(data) { 
        $('#chatterNewest').html(data);
    }
);

$.get('/ajax/chatter/photos', function(data) { 
        $('#chatterPics').html(data);
    }
);

$.get('/ajax/chatter/conversations', function(data) { 
        $('#chatterConversation').html(data);
    }
);

$.get('/ajax/chatter/questions', function(data) { 
        $('#chatterQuestions').html(data);
    }
);