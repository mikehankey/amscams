import hmac
import base64
import urllib.parse
import time
from hashlib import sha256
message = "/download/cat.jpg"
secret = "mysecrettoken"
separator = "?verify="
timestamp = str(int(time.time()))
digest = hmac.new((secret).encode('utf8'), "{}{}".format(message,timestamp).encode('utf8'), sha256)
token = urllib.parse.quote_plus(base64.b64encode(digest.digest()))
print("{}{}{}-{}".format(message, separator, timestamp, token))
