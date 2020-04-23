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
    for key, value in synonyms.items():
        for synonym in value:
            synonym_count += 1
            logging.debug(f"Counted '{synonym}' in '{key}', current total: {synonym_count}")

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
    """Return the line displaying the given word in bold drawn at the top
of the terminal."""
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
    """Return the line prompting the user for the various options in the
shortlisting phase. Drawn at the bottom of the terminal."""
    line = curses.newwin(1, max_x, max_y - 1, 0)
    line.addstr(0, 0, "Shortlist word? (y/n/s/q/?) ")

    return line


def show_options_for_synonym(word, synonym, shortlist, screen):
    """Prompt the user for a single synonym. Returns a tuple containing
the shortlist with any applicable additions, and a boolean that equals
True if the user chose to skip the word."""
    max_y, max_x = screen.getmaxyx()

    should_skip_word = False
    showing_help = False

    while True:
        if not showing_help:
            bottom_line = get_prompt_line(max_y, max_x)
            middle_line = get_synonym_line(synonym, max_y, max_x)
            top_line = get_word_line(word, max_y, max_x)
            top_line.refresh()
            middle_line.refresh()
            bottom_line.refresh()

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
                showing_help = True

        elif showing_help:
            help_window = get_help_window(max_y, max_x)
            help_window.refresh()

            curses.curs_set(0)
            c = help_window.getch()

            if c == ord('?'):
                screen.erase()
                screen.refresh()
                showing_help = False

    return (shortlist, should_skip_word)



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

            shortlist, should_skip_word = show_options_for_synonym(word, synonym,
                                                                   shortlist, screen)

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


def text_dump(synonyms, fp):
    for key, value in synonyms.items():
        fp.write(key.upper() + "\n")
        for synonym in value:
            fp.write(synonym + "\n")
        fp.write("\n")


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
    logging.debug(f"Synonyms: {synonyms}")
    logging.debug(f"Shortlist: {shortlist}")
    screen.addstr(2, 0, f"Total synonyms received: {synonym_count}")
    screen.addstr(3, 0, f"Total shortlisted: {shortlist_count}")
    screen.addstr(5, 0, f"CHOSEN WORDS")

    # Print synonyms
    for index, (word, value) in enumerate(shortlist.items()):
        screen.addstr(index + 6, 0,
                      format_with_commas(shortlist[word]), curses.A_BOLD)

    # Display saving options
    screen.addstr(max_y - 5, 0, "Choose option:")
    screen.addstr(max_y - 4, 0, "1", curses.A_BOLD)
    screen.addstr(max_y - 4, 1, " - Save to text file")
    screen.addstr(max_y - 3, 0, "2", curses.A_BOLD)
    screen.addstr(max_y - 3, 1, " - Save to JSON")
    screen.addstr(max_y - 2, 0, "3", curses.A_BOLD)
    screen.addstr(max_y - 2, 1, " - Quit without saving")
    screen.refresh()

    while True:
        c = screen.getch()

        if c == ord('1'):
            with open("saved-synonyms.txt", "w") as fp:
                text_dump(shortlist, fp)
            break
        elif c == ord('2'):
            with open("saved-synonyms.json", "w") as fp:
                json.dump(shortlist, fp)
            break
        elif c == ord('3'):
            break


if __name__ == "__main__":
    curses.wrapper(main)
