import sys
path="/wwwhome/piratehr/"
if not path in sys.path: sys.path.append(path)
from piratehr import app as application
