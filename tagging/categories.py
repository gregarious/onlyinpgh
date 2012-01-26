import csv,os

def load_category_map(map_type):
    '''
    Returns a dict mapping a string to a list of tag strings.

    Map type is a string among:
    - 'google_places'
    '''
    map_dir = os.path.join(os.path.dirname(__file__),'category_maps')
    if map_type == 'google_places':
        csv_file = os.path.join(map_dir,'google_places.csv')
    
    category_map = {}
    with open(csv_file) as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 1:
                category_map[row[0].strip()] = [f.strip() for f in row[1:]]

    return category_map 