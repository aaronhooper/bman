from urllib.parse import urljoin, urlparse, urlunparse
from os.path import join

import requests


API_LOC = "https://words.bighugelabs.com/api/2"
RES_FORMAT = "json"
API_KEY_FILE = "api_key"

DUMMY_RESULTS = {'liquid': ['swimming', 'limpid', 'melted', 'liquified', 'fluent', 'fluid', 'smooth', 'liquidness', 'liquidity', 'liquid state', 'consonant', 'fluid', 'state', 'state of matter'], 'great': ['outstanding', 'bang-up', 'bully', 'corking', 'cracking', 'dandy', 'groovy', 'keen', 'neat', 'nifty', 'peachy', 'slap-up', 'swell', 'smashing', 'capital', 'majuscule', 'enceinte', 'expectant', 'gravid', 'avid', 'big', 'eager', 'heavy', 'large', 'not bad', 'with child', 'zealous', 'achiever', 'succeeder', 'success', 'winner'], 'forest': ['wood', 'woods', 'woodland', 'timberland', 'timber', 'biome', 'botany', 'dry land', 'earth', 'flora', 'ground', 'land', 'solid ground', 'terra firma', 'vegetation', 'afforest', 'plant', 'set']}


def _get_synonyms_from_api(word):
    api_key = open(API_KEY_FILE, "r").readline().strip()
    parsed_api_loc = urlparse(API_LOC)
    full_req_path = join(parsed_api_loc.path, api_key, word, RES_FORMAT)
    parsed_url = parsed_api_loc._replace(path=full_req_path)
    req_url = urlunparse(parsed_url)

    res = requests.get(req_url)
    json_dict = res.json()

    synonyms = []
    for word_group in json_dict:
        if 'syn' in json_dict[word_group]:
            synonyms += json_dict[word_group]['syn']

    return synonyms


def _get_synonyms(*words, **options):
    if not options['should_hit_api']:
        return DUMMY_RESULTS

    results = {}

    for word in words:
        results[word] = _get_synonyms_from_api(word)

    return results


def get_synonyms(*words):
    return _get_synonyms(*words, should_hit_api=True)


def main():
    words = ["liquid", "great", "forest"]
    print(get_synonyms(*words))

    
if __name__ == "__main__":
    main()
