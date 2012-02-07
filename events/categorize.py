from onlyinpgh.events.models import Meta

category_keywords_map = {   
    'Educational': [
        'g20',
        'informational meeting',
        'knowledge',
        'teacher',
        'office hours',
        'university',
        'project',
        'career',
        'carlow',
        'duquesne university',
        'library',
        'carnegie mellon',
        'workshop',
        'college',
        'education',
        'educational',
        'legal',
        'zoo',
        'book',
        'reading',
        'class',
        'study group',
        'philosophy',
        'exam',
        'faculty',
        'law',
        'forum',
        'technical',
        'study',
        'academic',
    ],
    'Theater': [
        'production',
        'broadway',
        'matinee',
        'one-act',
        'cinema',
        'movie',
        'film',
        'performance',
        'stage',
        'theater',
    ],
    'Arts': [
        'arts',
        'exhibition',
        'sculpture',
        'exhibit',
        'gallery',
        'installation',
        'avant',
        'crafts',
        'painting'
    ],
    'Food & Drink': [
        'budweiser',
        'turkey',
        'tasting',
        'menu',
        'beer',
        'coffee',
        'food',
        'brunch',
        'grill',
        'bbq',
        'miller lite',
        'liquor',
        'breakfast',
        'drinks',
        'drink specials',
        'cafe',
        'drinking game',
        'drink',
        'buffet',
        'lunch',
        'scotch',
        'dinner',
        'brew',
        'wine'
    ],
    'Music': [
        'dance',
        'listening party',
        'radio',
        'carols',
        'music',
        'choir',
        'preview',
        'drum',
        'karaoke',
        'studio',
        'tunes',
        'trio',
        'concert',
        'band',
        'dj',
        'mic',
        'jam session',
        'rehearsal',
        'audition',
        'recital',
        'quartet',
    ],
    'Shopping': [
        'shop',
        'market',
        'store',
        'shopping',
        'blowout',
        'gift',
        'summer special',
        'black friday',
        'sale',
        'jewelry',
        'flea market',
        'retail',
    ],
    'Sports & Outdoors': [
        'camping trip',
        'walk',
        '5k',
        'sports practice',
        'cycling',
        'sports',
        'bike',
        'hockey',
        'swim',
        'trail',
        'roadtrip',
        'fitness',
        'river',
        'bicycle',
        'group trip',
        'pick-up',
        'martial',
        'marathon',
        'yoga',
        'football',
        'baseball',
        'tournament',
        'sporting event',
        'daytrip',
        'pep rally'
    ]
}

import re
category_regex_map = {}
for category, keywords in category_keywords_map.items():
    keywords = [re.escape(kw) for kw in keywords]
    category_regex_map[category] = re.compile(r'(%s)' % ')|('.join(keywords))

def add_event_oldtypes(event):
    '''
    Adds oldtype meta entries to the given event based on keyword matching
    '''
    content = event.name + "; " + event.description
    categories = [category for category,regex in category_regex_map.items() if regex.search(content)]

    if len(categories) == 0:
        categories = ['General Fun']

    for category in categories:
        Meta.objects.get_or_create(event=event,
                                    meta_key='oldtype',
                                    meta_value=category)
