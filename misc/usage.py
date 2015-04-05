# vim: fileencoding=utf-8

"""
Embed the py2deb usage instructions inside the README.

This Python script takes the py2deb usage instructions (``py2deb --help``),
reformats them to reStructuredText and embeds them in the README. I like to
have up to date usage instructions embedded in the README, but what I really
don't like is reformatting the usage instructions as reStructuredText
manually every time. I'm also not going to write the usage instructions in
reStructuredText format because they're supposed to be readable as plain text
on a terminal by people who don't know reStructuredText :-).

This ad-hoc script solves the problem nicely for now. It may eat the README at
a later point in time, but it's in version control, so who cares? (as long as I
notice before publishing, but I *always* review changes before committing).
"""

import re
import codecs
from py2deb.cli import __doc__ as usage_message

def embed_usage(readme, encoding='UTF-8'):
    """Reformat the py2deb usage instructions and embed them in the README."""
    with codecs.open(readme, 'r', encoding) as handle:
        contents = handle.read()
    blocks = contents.split('\n\n')
    # Find the index of the block with the "Usage" heading.
    start_index = 0
    while start_index < len(blocks) and not is_heading(blocks[start_index], "Usage"):
        start_index += 1
    # Find the index of the first block after the "Usage" heading that contains
    # a new heading.
    end_index = start_index + 1
    while end_index < len(blocks) and not is_heading(blocks[end_index]):
        end_index += 1
    # Combine the text before the usage instructions, the reformatted usage
    # instructions and the text after the usage instructions.
    blocks_before = blocks[:start_index + 1]
    blocks_after = blocks[end_index:]
    blocks = blocks_before + [reformat_usage()] + blocks_after
    with codecs.open(readme, 'w', encoding) as handle:
        handle.write('\n\n'.join(blocks))

def is_heading(block, text=None):
    """Check if a block looks like a reStructuredText heading."""
    lines = block.splitlines()
    return (len(lines) == 2 and
            (text is None or compact(lines[0]) == compact(text)) and
            len(lines[0]) == len(lines[1]) and
            len(set(lines[1])) == 1)

def reformat_usage():
    """Reformat the py2deb usage instructions (``py2deb --help``) to reStructuredText."""
    # Strip leading and trailing whitespace from the docstring.
    text = usage_message.strip()
    # Decode the docstring to Unicode so we can inject Unicode characters.
    text = text.decode('UTF-8')
    # Process each paragraph in the docstring separately.
    return "\n\n".join(reformat_block(b) for b in text.split('\n\n'))

def reformat_block(block):
    """Reformat a block of the usage instructions."""
    if block.startswith('Usage:'):
        # Reformat the "Usage:" line to highlight "Usage:" in bold and show the
        # remainder of the line as preformatted text.
        tokens = block.split()
        return "**%s** ``%s``" % (tokens[0], ' '.join(tokens[1:]))
    if block == 'Supported options:':
        # Reformat the "Supported options:" line to highlight it in bold.
        return "**%s**" % block
    if re.match(r'^\s+\$\s+', block):
        # Reformat shell transcripts into code blocks.
        lines = block.splitlines()
        lines.insert(0, '.. code-block:: sh')
        lines.insert(1, '')
        return "\n".join(lines)
    if re.match('^\s+-{1,2}\w', block):
        # Reformat command line options.
        return ", ".join("``%s``" % o for o in re.split(r",\s+", block.strip()))
    # Compact whitespace in the remaining blocks.
    block = compact(block)
    # Change the quoting so it doesn't trip up DocUtils.
    block = re.sub("`(.+?)'", ur'“\1”', block)
    # Change environment variables to use preformatted text.
    block = re.sub(r'(\$\w+)', r'``\1``', block)
    # Quote a stray "emphasis start string".
    block = block.replace('*.deb', '``*.deb``')
    return block

def compact(text):
    """Compact whitespace in a string."""
    return " ".join(text.split())

if __name__ == '__main__':
    embed_usage('README.rst')
