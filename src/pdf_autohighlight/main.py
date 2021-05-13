import logging
import os
import os.path
import shutil
import sys
import warnings

from pathlib import Path

import click
import fitz

LOG = logging.getLogger('pdf-autohighlight')

COLOR_MAP = {
    'yellow': [1.0, 1.0, 0.0],
    'green': [0.5, 1.0, 0.0],
    'blue': [0.0, 0.75, 1.0],
    'pink': [1.0, 0.5, 1.0],
    'red': [1.0, 0.5, 0.5],
    'grey': [0.7, 0.7, 0.7],
    'orange': [1.0, 0.5, 0.0],
    'purple': [0.5, 0.5, 1.0],
}


def _log_exception(extype, value, trace):
    """
    Hook to log uncaught exceptions to the logging framework. Register this as
    the excepthook with `sys.excepthook = log_exception`.
    """
    LOG.exception("Uncaught exception: ", exc_info=(extype, value, trace))


def _setup_logging(log_file=None, activate_warnings=True):
    """
    Sets up the logging framework to log to the given log_file and to STDOUT.
    If the path to the log_file does not exist, directories for it will be
    created.
    """
    handlers = []
    if log_file:
        if os.path.exists(log_file):
            backup = '{}.1'.format(log_file)
            shutil.move(log_file, backup)
        file_handler = logging.FileHandler(log_file, 'w', 'utf-8')
        handlers.append(file_handler)

    term_handler = logging.StreamHandler()
    handlers.append(term_handler)
    fmt = '%(asctime)s %(levelname)-8s %(message)s'
    logging.basicConfig(handlers=handlers, format=fmt, level=logging.DEBUG)

    sys.excepthook = _log_exception

    if activate_warnings:
        warnings.simplefilter('default')
        logging.captureWarnings(True)


def _read_search_terms(searches_path):
    searches = []
    with open(searches_path) as infile:
        for line in infile:
            if not line:
                continue
            search = line.strip()
            term, color = search.split('=')
            if color not in COLOR_MAP:
                LOG.error('Invalid color for term: %s = %s', term, color)
                return None

            if search:
                searches.append((term, color))
    return searches


def process_pdf(pdf_in, pdf_out, searches):
    LOG.info('Handling PDF: %s', pdf_in.name)
    doc = fitz.open(str(pdf_in))

    for idx, page in enumerate(doc):
        for term, color in searches:
            instances = page.search_for(' ' + term + ' ', quads=True)
            for instance in instances:
                quad_str = '[{}, {}], [{}, {}], [{}, {}], [{}, {}]'
                quad_str = quad_str.format(instance.ll.x, instance.ll.y,
                                           instance.ul.x, instance.ul.y,
                                           instance.ur.x, instance.ur.y,
                                           instance.lr.x, instance.lr.y)

                LOG.debug('Highlighting instance of "%s" @ %s:(%s)',
                          term, idx, quad_str)

                annot = page.add_highlight_annot(instance)

                colors = annot.colors
                colors['stroke'] = COLOR_MAP[color]
                annot.set_colors(colors)

                annot.update()

    LOG.info('Saving annotated PDF: %s', pdf_out)
    doc.save(pdf_out, garbage=4, deflate=True, clean=True)


@click.command()
@click.argument('pdf-dir', type=click.Path(file_okay=False, exists=True))
@click.argument('out-dir', type=click.Path(file_okay=False))
@click.argument('searches', type=click.Path(dir_okay=False, exists=True))
def cli(pdf_dir, out_dir, searches):
    _setup_logging(log_file='pdfautohighlight.log')

    pdf_dir = Path(pdf_dir)
    out_dir = Path(out_dir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True)

    searches = _read_search_terms(searches)
    LOG.info('Starting PDF Auto-Highlighting.')
    LOG.info('Input PDF path:  %s', str(pdf_dir))
    LOG.info('Output PDF path: %s', str(out_dir))
    LOG.info('Highlighted search terms:')
    for search in searches:
        LOG.info('\t%s', search)

    for pdf_in in pdf_dir.glob('*.pdf'):
        pdf_out = out_dir / pdf_in.name
        process_pdf(pdf_in, pdf_out, searches)


if __name__ == '__main__':
    cli(obj={})
