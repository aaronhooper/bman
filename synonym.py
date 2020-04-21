import curses
from os.path import join
import sys
import time
from urllib.parse import urljoin, urlparse, urlunparse

import requests


RES_FORMAT = "json"
ENABLE_API = False
API_KEY_FILE = "api_key"

DUMMY_RESULTS = {'liquid': ['swimming', 'limpid', 'melted', 'liquified', 'fluent', 'fluid', 'smooth', 'liquidness', 'liquidity', 'liquid state', 'consonant', 'fluid', 'state', 'state of matter'], 'great': ['outstanding', 'bang-up', 'bully', 'corking', 'cracking', 'dandy', 'groovy', 'keen', 'neat', 'nifty', 'peachy', 'slap-up', 'swell', 'smashing', 'capital', 'majuscule', 'enceinte', 'expectant', 'gravid', 'avid', 'big', 'eager', 'heavy', 'large', 'not bad', 'with child', 'zealous', 'achiever', 'succeeder', 'success', 'winner'], 'forest': ['wood', 'woods', 'woodland', 'timberland', 'timber', 'biome', 'botany', 'dry land', 'earth', 'flora', 'ground', 'land', 'solid ground', 'terra firma', 'vegetation', 'afforest', 'plant', 'set']}


def _get_synonyms_from_bighugelabs(word):
    """Returns a list of synonyms from the Big Thesaurus API."""
    API_LOC = "https://words.bighugelabs.com/api/2"
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
        results[word] = _get_synonyms_from_bighugelabs(word)

    return results


def get_synonyms(*words):
    """Returns a dictionary with a words to synonyms mapping."""
    return _get_synonyms(*words, should_hit_api=ENABLE_API)


def start_shortlisting(screen, synonyms):
    """Prompt the user to choose synonyms to be included in the
shortlist. Returns the shortlist."""

    # Get terminal size
    max_y, max_x = screen.getmaxyx()
    
    # Set up line windows
    top_line = curses.newwin(1, max_x, 0, 0)
    middle_line = curses.newwin(1, max_x, round(max_y / 2), 0)
    bottom_line = curses.newwin(1, max_x, max_y - 1, 0)

    # Show cursor
    curses.curs_set(1)

    screen.erase()
    shortlist = {}

    for word in synonyms:
        top_line.erase()
        top_line.addstr(0, 0, "Synonym for")
        top_line.addstr(0, 12, f"{word}", curses.A_BOLD)
        top_line.refresh()
 
        for synonym in synonyms[word]:
            middle_line.erase()
            middle_line.addstr(0, 2, f"==> ")
            middle_line.addstr(0, 7, synonym, curses.A_BOLD)
            middle_line.refresh()
            bottom_line.addstr(0, 0, "Shortlist word? (y/n/s/q/?) ")
            should_skip_word = False

            # User options loop
            while True:
                c = bottom_line.getch()

                if c == ord('y'):
                    shortlist[word] = synonym
                    break
                elif c == ord('n'):
                    break
                elif c == ord('s'):
                    should_skip_word = True
                    break
                elif c == ord('q'):
                    sys.exit(0)

            if should_skip_word:
                break

    curses.curs_set(0)

    return shortlist


def main(screen):
    words = ["liquid", "great", "forest"]

    # Get terminal size
    max_y, max_x = screen.getmaxyx()

    # Hide cursor
    curses.curs_set(0)

    # Fetch synonyms
    screen.addstr(max_y - 1, 0, "Fetching results ...")
    screen.refresh()
    synonyms = get_synonyms(*words)

    # Simulate latency for dummy results
    time.sleep(2)

    # Begin shortlisting
    shortlist = start_shortlisting(screen, synonyms)

    screen.clear()
    screen.addstr(0, 0, str(list(map(lambda x: x.upper(), shortlist.keys()))))
    screen.refresh()

    while True:
        continue


if __name__ == "__main__":
    curses.wrapper(main)
