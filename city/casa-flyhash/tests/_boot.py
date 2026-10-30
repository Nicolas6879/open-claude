"""Arranque comun de los tests: usa el venv si el python del sistema no tiene scipy/numba (ver README)."""
import os, sys
VENV = os.environ.get('FLYHASH_PY', '/tmp/claude-0/-home-user-open-claude/e7f872ff-c04d-5af4-a3a1-8d2199c39026/scratchpad/venv/bin/python')
try:
    import scipy, numba, sklearn, pandas  # noqa
except ImportError:
    if os.path.exists(VENV) and os.environ.get('FLYHASH_REEXEC') != '1':
        os.environ['FLYHASH_REEXEC'] = '1'; os.execv(VENV, [VENV, '-B', '-I'] + sys.argv)
    raise
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'src'))
