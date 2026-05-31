import urllib.request
import urllib.error
import json

req = urllib.request.Request(
    'https://innovahack-gcrh.onrender.com/visitas/2/finalizar', 
    data=b'{"latitud_actual": -16.5, "longitud_actual": -68.1}', 
    headers={'Content-Type': 'application/json'}
)

try: 
    print(urllib.request.urlopen(req).read())
except urllib.error.HTTPError as e: 
    print(e.code, e.read())
