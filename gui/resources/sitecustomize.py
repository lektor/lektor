import sys
import site
site.ENABLE_USER_SITE = False

if sys.platform == 'darwin':
    sys.path[:] = [x for x in sys.path
                   if not x.startswith(('/Library', '/System'))]
