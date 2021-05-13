import setuptools
import os
import os.path


def long_description():
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, 'README.md')) as infile:
        return infile.read()


setuptools.setup(long_description=long_description(),
                 long_description_content_type='text/markdown')
