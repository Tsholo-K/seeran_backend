import redis
from decouple import config
import ssl


redis_client = redis.StrictRedis(
    host=config('CACHE_LOCATION'),
    port=6378,
    ssl=True,
    ssl_cert_reqs=ssl.CERT_REQUIRED,
    ssl_ca_certs=config('SERVER_CA_CERT')
)
