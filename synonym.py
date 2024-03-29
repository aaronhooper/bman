import curses
import json
from os.path import join
import sys
from urllib.parse import urlparse, urlunparse
import requests

from settings import ENABLE_API, API_KEY_FILE, TEST_DATA_FILE, RES_FORMAT

import logging
logging.basicConfig(filename="debug.log", level=logging.DEBUG)


def main(screen):

    words = sys.argv[1:]
    max_y, max_x = screen.getmaxyx()
    curses.curs_set(0)
    screen.addstr(max_y - 1, 0, "Fetching results ...")
    screen.refresh()
    synonyms = get_synonyms(*words)
    shortlist = start_shortlisting(screen, synonyms)
    show_summary(synonyms, shortlist, screen)
    FILENAME_PART = "saved-synonyms"

    while True:
        c = screen.getch()

        if c == ord('1'):
            file_ext = "txt"
        elif c == ord('2'):
            file_ext = "json"
        elif c == ord('3'):
            break

        dump_file(shortlist, FILENAME_PART, file_ext)
        break


def get_synonyms(*words):
    """Get synonyms of one or more words."""

    if not ENABLE_API:
        with open(TEST_DATA_FILE, 'r') as json_file:
            test_data = json.load(json_file)
        return test_data

    results = {}

    for word in words:
        results[word] = get_synonyms_from_bighugelabs(word)

    return results


def start_shortlisting(screen, synonyms):
    """Prompt the user to choose synonyms."""

    max_y, max_x = screen.getmaxyx()
    screen.erase()
    shortlist = {}

    # Assign the appropriate keys to lists, so that appending
    # initially doesn't throw an error.
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
            shortlist, should_skip_word = \
                show_options_for_synonym(word, synonym, shortlist, screen)

            if should_skip_word:
                break

    curses.curs_set(0)
    logging.debug(f"Shortlist: {shortlist}")

    return shortlist


def show_summary(synonyms, shortlist, screen):
    """Show a summary of the chosen words and synonyms."""

    max_y, max_x = screen.getmaxyx()
    formatted_words = format_with_commas(shortlist.keys())
    screen.clear()

    screen.addstr(0, 0, "SUMMARY")
    synonym_count = count_synonyms(synonyms)
    shortlist_count = count_synonyms(shortlist)
    logging.debug(f"Synonyms: {synonyms}")
    logging.debug(f"Shortlist: {shortlist}")
    screen.addstr(1, 0, f"Total synonyms received: {synonym_count}")
    screen.addstr(2, 0, f"Total shortlisted: {shortlist_count}")

    screen.addstr(4, 0, "WORDS")
    screen.addstr(5, 0, formatted_words, curses.A_BOLD)

    screen.addstr(7, 0, f"SYNONYMS")
    for index, (word, value) in enumerate(shortlist.items()):
        screen.addstr(index + 8, 0,
                      format_with_commas(shortlist[word]), curses.A_BOLD)

    screen.addstr(max_y - 5, 0, "Choose option:")
    screen.addstr(max_y - 4, 0, "1", curses.A_BOLD)
    screen.addstr(max_y - 4, 1, " - Save to text file")
    screen.addstr(max_y - 3, 0, "2", curses.A_BOLD)
    screen.addstr(max_y - 3, 1, " - Save to JSON")
    screen.addstr(max_y - 2, 0, "3", curses.A_BOLD)
    screen.addstr(max_y - 2, 1, " - Quit without saving")
    screen.refresh()


def dump_file(shortlist, filename, file_ext):
    """Save the synonyms to a file with the format of file_ext."""

    with open(filename + "." + file_ext, "w") as fp:
        if file_ext == "json":
            json.dump(shortlist, fp)
        elif file_ext == "txt":
            text_dump(shortlist, fp)


def text_dump(synonyms, fp):
    """Save the synonyms to a text file."""

    for key, value in synonyms.items():
        fp.write(key.upper() + "\n")

        for synonym in value:
            fp.write(synonym + "\n")
        fp.write("\n")


def get_synonyms_from_bighugelabs(word):
    """Get synonyms of a word from Big Thesaurus."""

    API_LOC = "https://words.bighugelabs.com/api/2"
    api_key = open(API_KEY_FILE, "r").readline().strip()
    parsed_api_loc = urlparse(API_LOC)
    full_req_path = join(parsed_api_loc.path, api_key, word, RES_FORMAT)
    parsed_url = parsed_api_loc._replace(path=full_req_path)
    req_url = urlunparse(parsed_url)
    synonyms = []

    try:
        res = requests.get(req_url)
        res.raise_for_status()
        json_dict = res.json()

        for word_group in json_dict:
            if 'syn' in json_dict[word_group]:
                synonyms += json_dict[word_group]['syn']

    except requests.exceptions.HTTPError as e:
        logging.info(f"An error occured while retrieving synonyms for '{word}': {e}")

    return synonyms


def get_word_line(word, max_y, max_x):
    """Create the current word line."""

    line = curses.newwin(1, max_x, 0, 0)
    line.addstr(0, 0, "Synonym for")
    line.addstr(0, 12, f"{word}", curses.A_BOLD)

    return line


def get_synonym_line(synonym, max_y, max_x):
    """Create the synonym line."""

    line = curses.newwin(1, max_x, round(max_y / 3), 0)
    line.addstr(0, 2, f"==> ")
    line.addstr(0, 7, synonym, curses.A_BOLD)

    return line


def show_options_for_synonym(word, synonym, shortlist, screen):
    """Prompt the user for a single synonym."""

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


def format_with_commas(words):
    """Format the list of words with commas."""

    output = ""

    for word in words:
        output += word + ", "

    return output[:len(output) - 2]


def count_synonyms(synonyms):
    """Count the synonyms in the dictionary."""

    synonym_count = 0

    for key, value in synonyms.items():
        for synonym in value:
            synonym_count += 1

    return synonym_count


def get_help_window(max_y, max_x):
    """Create the help window."""

    HELP_OPTIONS = {
        "y": "yes",
        "n": "no",
        "s": "skip rest of synonyms for this word",
        "q": "quit",
        "?": "show/hide this window"
    }

    help_window = curses.newwin(max_y, max_x, 0, 0)
    help_window.addstr(0, 0, "HELP")

    for i, (key, value) in enumerate(HELP_OPTIONS.items()):
        help_window.addstr(i + 1, 0, key, curses.A_BOLD)
        help_window.addstr(i + 1, 1, f" - {value}")

    return help_window


def get_prompt_line(max_y, max_x):
    """Create the question prompt."""

    line = curses.newwin(1, max_x, max_y - 1, 0)
    line.addstr(0, 0, "Shortlist word? (y/n/s/q/?) ")

    return line


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(f"Usage: ./{sys.argv[0]} <word> ...")
        sys.exit(1)

    curses.wrapper(main)
