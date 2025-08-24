#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kindle Clippings Parser

This script parses the "My Clippings.txt" file from Amazon Kindle devices
and converts the highlights and notes into a more readable markdown format.
"""

import argparse
import json
import os
import re
import logging
import dateutil.parser

# Import local modules
from utils import BasicEqualityMixin, DatetimeJSONEncoder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# E.g. Friday, May 13, 2016 11:23:26 PM
DATETIME_FORMAT = '%A, %B %d, %Y %I:%M:%S %p'
CLIPPINGS_SEPARATOR = '=========='

class Document(BasicEqualityMixin):
    """Document (e.g. book, article) the clipping originates from.

    A document has a title, and one or multiple authors (in a string).
    """

    PATTERN = re.compile(r'^(?P<title>.+) \((?P<authors>.+?)\)$')

    def __init__(self, title, authors):
        self.title = title
        self.authors = authors

    def __str__(self):
        return '{title} ({authors})'.format(title=self.title,
                                            authors=self.authors)

    def to_dict(self):
        return self.__dict__

    @classmethod
    def parse(cls, line):
        match = re.match(cls.PATTERN, line)
        if match:
            title = match.group('title')
            authors = match.group('authors')
            return cls(title, authors)
        else:
            # If pattern doesn't match, assume entire line is title with unknown authors
            return cls(line.strip(), "Unknown")

class Location(BasicEqualityMixin):
    """Location of the clipping in the document.

    A location consists of a begin-end range.
    """

    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    def __str__(self):
        if self.begin == self.end:
            return str(self.begin)
        else:
            return '{0}-{1}'.format(self.begin, self.end)

    def to_dict(self):
        return self.__dict__

    @classmethod
    def parse(cls, string):
        ranges = string.split('-')
        if len(ranges) == 1:
            begin = end = ranges[0]
        else:
            begin = ranges[0]
            end = ranges[1]
        return cls(int(begin), int(end))

class Metadata(BasicEqualityMixin):
    """Metadata about the clipping:
    
        - The category of clipping (Note, Highlight, or Bookmark);
        - The location within the document;
        - The timestamp of the clipping;
        - The page within the document (not always present).
    """

    PATTERN = re.compile(r'^- Your (?P<category>\w+) '
                         + r'(on|at) ((P|p)age (?P<page>\d+) \| )?'
                         + r'(L|l)ocation (?P<location>\d+(-\d+)?) \| '
                         + r'Added on (?P<timestamp>.+)$')

    HOUR_PATTERN = re.compile(r'0(\d:\d{2}:\d{2})')

    def __init__(self, category, location, timestamp, page=None):
        self.category = category
        self.location = location
        self.timestamp = timestamp
        self.page = page

    def __str__(self):
        page_string = '' if self.page is None else 'page {0} | '.format(
            self.page)

        # Remove leading zero's from the timestamp.
        # They are not present in the Kindle format, but can't be avoided
        # in strftime.
        timestamp_str = self.timestamp.strftime(DATETIME_FORMAT)
        timestamp_str = re.sub(self.HOUR_PATTERN, r'\1', timestamp_str)

        return '- Your {category} on {page}Location {location} | Added on {timestamp}'.format(
            category=self.category.title(),
            page=page_string,
            location=self.location,
            timestamp=timestamp_str,
        )

    def to_dict(self):
        return {
            'category': self.category,
            'location': self.location.to_dict(),
            'timestamp': self.timestamp,
            'page': self.page,
        }

    @classmethod
    def parse(cls, line):
        match = re.match(cls.PATTERN, line)
        if not match:
            raise ValueError(f"Could not parse metadata line: {line}")
            
        category = match.group('category')
        location = Location.parse(match.group('location'))
        timestamp = dateutil.parser.parse(match.group('timestamp'))
        try:
            page = int(match.group('page'))
        except (TypeError, ValueError):
            page = None
        return cls(category, location, timestamp, page)

class Clipping(BasicEqualityMixin):
    """Kindle clipping: content associated with a particular document"""

    def __init__(self, document, metadata, content):
        self.document = document
        self.metadata = metadata
        self.content = content

    def __str__(self):
        return '\n'.join([str(self.document), str(self.metadata), str(self.content)])

    def to_dict(self):
        return {
            'document': self.document.to_dict(),
            'metadata': self.metadata.to_dict(),
            'content': self.content,
        }

def parse_clippings(clippings_file):
    """Take a file containing clippings, and return a list of objects."""
    
    # Last separator not followed by an entry
    entries = clippings_file.read().split(CLIPPINGS_SEPARATOR)[:-1]
    clippings = []

    for entry in entries:
        lines = entry.strip().splitlines()
        if len(lines) < 3:
            continue

        try:
            document_line = lines[0]
            document = Document.parse(document_line)

            metadata_line = lines[1]
            metadata = Metadata.parse(metadata_line)

            content = '\n'.join(lines[3:]).strip()

            clippings.append(Clipping(document, metadata, content))
        except Exception as e:
            logger.warning(f"Error parsing clipping: {e}")
            continue

    return clippings

def as_dicts(clippings):
    """Return the clippings as python dictionaries.

    The result can be converted to JSON, or manipulated directly in Python,
    for instance.
    """
    return [clipping.to_dict() for clipping in clippings]

def group_clippings_by_book(clippings):
    """Group clippings by book title.
    
    Args:
        clippings (list): List of clipping dictionaries
        
    Returns:
        dict: Dictionary with book titles as keys and lists of clippings as values
    """
    books = {}
    for clipping in clippings:
        title = clipping.document.title
        if title not in books:
            books[title] = {
                "author": clipping.document.authors,
                "clippings": []
            }
        books[title]["clippings"].append(clipping)
    
    # Sort clippings by location
    for book in books.values():
        book["clippings"].sort(key=lambda x: x.metadata.location.begin if hasattr(x.metadata.location, 'begin') else 0)
    
    return books

def group_clippings_by_book_dict(clippings_dict):
    """Group clippings by book title using dictionary format.
    
    Args:
        clippings_dict (list): List of clipping dictionaries
        
    Returns:
        dict: Dictionary with book titles as keys and lists of clippings as values
    """
    books = {}
    for clipping in clippings_dict:
        title = clipping['document']['title']
        if title not in books:
            books[title] = {
                "author": clipping['document']['authors'],
                "clippings": []
            }
        books[title]["clippings"].append(clipping)
    
    # Sort clippings by location
    for book in books.values():
        book["clippings"].sort(key=lambda x: int(x['metadata']['location']['begin']) if 'begin' in x['metadata']['location'] else 0)
    
    return books

def generate_markdown_output(books, output_file):
    """Generate markdown output from grouped clippings.
    
    Args:
        books (dict): Dictionary of books with their clippings
        output_file (str): Path to output file
    """
    logger.info(f"Generating markdown output to: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Kindle Clippings\n\n")
        
        for title, book_info in books.items():
            author = book_info["author"]
            clippings = book_info["clippings"]
            
            f.write(f"## {title}\n")
            if author and author != "Unknown":
                f.write(f"**Author:** {author}\n\n")
            
            # Group clippings by type
            highlights = [c for c in clippings if c['metadata']['category'] == "Highlight"]
            notes = [c for c in clippings if c['metadata']['category'] == "Note"]
            bookmarks = [c for c in clippings if c['metadata']['category'] == "Bookmark"]
            
            if highlights:
                f.write(f"### Highlights ({len(highlights)})\n\n")
                for i, highlight in enumerate(highlights, 1):
                    f.write(f"{i}. {highlight['content']}\n")
                    if highlight['metadata']['location']:
                        f.write(f"   - Location: {highlight['metadata']['location']['begin']}-{highlight['metadata']['location']['end']}\n")
                    if highlight['metadata']['page']:
                        f.write(f"   - Page: {highlight['metadata']['page']}\n")
                    f.write("\n")
            
            if notes:
                f.write(f"### Notes ({len(notes)})\n\n")
                for i, note in enumerate(notes, 1):
                    f.write(f"{i}. {note['content']}\n")
                    if note['metadata']['location']:
                        f.write(f"   - Location: {note['metadata']['location']['begin']}-{note['metadata']['location']['end']}\n")
                    if note['metadata']['page']:
                        f.write(f"   - Page: {note['metadata']['page']}\n")
                    f.write("\n")
            
            if bookmarks:
                f.write(f"### Bookmarks ({len(bookmarks)})\n\n")
                for i, bookmark in enumerate(bookmarks, 1):
                    f.write(f"{i}. Bookmark\n")
                    if bookmark['metadata']['location']:
                        f.write(f"   - Location: {bookmark['metadata']['location']['begin']}-{bookmark['metadata']['location']['end']}\n")
                    if bookmark['metadata']['page']:
                        f.write(f"   - Page: {bookmark['metadata']['page']}\n")
                    f.write("\n")
            
            f.write("---\n\n")
    
    logger.info("Markdown output generated successfully")

def main():
    """Main function to parse clippings and generate output."""
    parser = argparse.ArgumentParser(description="Parse Kindle clippings file and generate markdown output")
    parser.add_argument("input_file", nargs='?', default="input/My Clippings.txt", help="Path to the My Clippings.txt file")
    parser.add_argument("-o", "--output", default="clippings.md", help="Output file name (default: clippings.md)")
    parser.add_argument("-j", "--json", action="store_true", help="Also output JSON format")
    
    args = parser.parse_args()
    
    # Parse the clippings file
    input_file = args.input_file
    if not os.path.exists(input_file):
        # Try to find the file in the input directory as fallback
        input_file = os.path.join("input", os.path.basename(args.input_file))
    
    try:
        logger.info(f"Parsing input file: {input_file}")
        with open(input_file, "r", encoding='utf-8') as clippings_file:
            clippings = parse_clippings(clippings_file)
    except FileNotFoundError:
        logger.error(f"File not found: {args.input_file}")
        return
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return
    
    if not clippings:
        logger.warning("No clippings found in the file")
        return
    
    # Convert to dictionaries for easier handling
    clip_dicts = as_dicts(clippings)
    
    # Group clippings by book using the dictionary format
    books = group_clippings_by_book_dict(clip_dicts)
    
    # Generate markdown output
    generate_markdown_output(books, args.output)
    
    # Optionally generate JSON output
    if args.json:
        json_output = args.output.replace(".md", ".json")
        logger.info(f"Generating JSON output to: {json_output}")
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(books, f, indent=2, cls=DatetimeJSONEncoder, ensure_ascii=False)
        logger.info("JSON output generated successfully")
    
    logger.info("Processing completed successfully")

if __name__ == "__main__":
    main()
