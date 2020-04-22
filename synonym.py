import curses
import json
from os.path import join
import sys
import time
from urllib.parse import urljoin, urlparse, urlunparse
import requests

import logging
logging.basicConfig(filename="debug.log", level=logging.DEBUG)


RES_FORMAT = "json"
ENABLE_API = False
API_KEY_FILE = "api_key"
TEST_DATA_FILE = "test_data.json"


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
        with open(TEST_DATA_FILE, 'r') as json_file:
            test_data = json.load(json_file)
        return test_data

    results = {}

    for word in words:
        results[word] = _get_synonyms_from_bighugelabs(word)

    return results


def get_synonyms(*words):
    """Returns a dictionary with a words to synonyms mapping."""
    return _get_synonyms(*words, should_hit_api=ENABLE_API)


def count_synonyms(synonyms):
    """Return the total number of synonyms in a word to synonym
dictionary."""
    synonym_count = 0
    for word in synonyms:
        for synonym in word:
            synonym_count += 1

    return synonym_count


def get_help_window(max_y, max_x):
    help_options = {
        "y": "yes",
        "n": "no",
        "s": "skip rest of synonyms for this word",
        "q": "quit",
        "?": "show/hide this window"
    }

    help_window = curses.newwin(max_y, max_x, 0, 0)
    help_window.addstr(0, 0, "HELP")

    for i, (key, value) in enumerate(help_options.items()):
        help_window.addstr(i + 1, 0, key, curses.A_BOLD)
        help_window.addstr(i + 1, 1, f" - {value}")

    return help_window


def get_word_line(word, max_y, max_x):
    line = curses.newwin(1, max_x, 0, 0)
    line.addstr(0, 0, "Synonym for")
    line.addstr(0, 12, f"{word}", curses.A_BOLD)

    return line


def get_synonym_line(synonym, max_y, max_x):
    """Return the line displaying the given synonym in bold. Drawn at the
first third of the terminal."""
    line = curses.newwin(1, max_x, round(max_y / 3), 0)
    line.addstr(0, 2, f"==> ")
    line.addstr(0, 7, synonym, curses.A_BOLD)

    return line


def get_prompt_line(max_y, max_x):
    line = curses.newwin(1, max_x, max_y - 1, 0)
    line.addstr(0, 0, "Shortlist word? (y/n/s/q/?) ")

    return line


def start_shortlisting(screen, synonyms):
    """Prompt the user to choose synonyms to be included in the
shortlist. Returns the shortlist."""

    # Get terminal size
    max_y, max_x = screen.getmaxyx()

    screen.erase()

    shortlist = {}
    for key in synonyms.keys():
        shortlist[key] = []

    for word in synonyms:
        if 'top_line' in locals():
            top_line.erase()
        top_line = get_word_line(word, max_y, max_x)
        top_line.refresh()
 
        for synonym in synonyms[word]:
            if 'middle_line' in locals():
                middle_line.erase()
            middle_line = get_synonym_line(synonym, max_y, max_x)
            middle_line.refresh()
            bottom_line = get_prompt_line(max_y, max_x)
            should_skip_word = False
            showing_help = False

            # User options loop
            while True:
                if not showing_help:
                    curses.curs_set(1)

                    c = bottom_line.getch()

                    if c == ord('y'):
                        shortlist[word] += [synonym]
                        logging.debug(f"Synonym added: {synonym}")
                        break
                    elif c == ord('n'):
                        break
                    elif c == ord('s'):
                        should_skip_word = True
                        break
                    elif c == ord('q'):
                        sys.exit(0)
                    elif c == ord('?'):
                        screen.erase()
                        help_window = get_help_window(max_y, max_x)
                        help_window.refresh()
                        showing_help = True

                elif showing_help:
                    curses.curs_set(0)
                    c = help_window.getch()

                    if c == ord('?'):
                        screen.erase()
                        screen.refresh()
                        showing_help = False
                        bottom_line = get_prompt_line(max_y, max_x)
                        middle_line = get_synonym_line(synonym, max_y, max_x)
                        top_line = get_word_line(word, max_y, max_x)
                        top_line.refresh()
                        middle_line.refresh()
                        bottom_line.refresh()

            if should_skip_word:
                break

    curses.curs_set(0)
    logging.debug(f"Shortlist: {shortlist}")

    return shortlist


def format_with_commas(words):
    """Separate the words in the list with commas."""
    output = ""
    for word in words:
        output += word + ", "

    return output[:len(output) - 2]


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

    # # Simulate latency for dummy results
    # time.sleep(2)

    # Begin shortlisting
    shortlist = start_shortlisting(screen, synonyms)

    # Print summary
    screen.clear()
    formatted_words = format_with_commas(shortlist.keys())
    screen.addstr(0, 0, "SUMMARY")
    screen.addstr(1, 0, "Given words: ")
    screen.addstr(1, 13, formatted_words, curses.A_BOLD)
    synonym_count = count_synonyms(synonyms)
    shortlist_count = count_synonyms(shortlist)
    screen.addstr(2, 0, f"Total synonyms shown: {synonym_count}")
    screen.addstr(3, 0, f"Total shortlisted: {shortlist_count}")
    screen.addstr(5, 0, f"SYNONYMS")

    # Print synonyms
    for index, (word, value) in enumerate(shortlist.items()):
        screen.addstr(index + 6, 0, format_with_commas(shortlist[word]))

    # Print dictionary
    screen.addstr(10, 0, str(shortlist))

    screen.refresh()

    while True:
        continue


if __name__ == "__main__":
    curses.wrapper(main)
