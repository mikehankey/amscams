from distutils.core import setup
from Cython.Build import cythonize
from Cython.Distutils import build_ext


setup(
name='fastThresh',
ext_modules=cythonize("fastThresh.pyx"),
)


