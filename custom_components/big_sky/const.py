"""Constants for the Big Sky Resort integration."""

DOMAIN = "big_sky"
NAME = "Big Sky Resort"

CONF_FEED_URL = "feed_url"
CONF_CREATE_RUN_ENTITIES = "create_run_entities"
CONF_CREATE_LIFT_ENTITIES = "create_lift_entities"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_FEED_URL = "https://reportpal-cdn.resorts-interactive.com/mtnxml/162"
DEFAULT_UPDATE_INTERVAL = 15
MIN_UPDATE_INTERVAL = 5
MAX_UPDATE_INTERVAL = 240

# The live feed is about 60 KB. Anything far larger is not the feed.
MAX_FEED_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT = 15

# Feed timestamps carry no zone; they are resort local time.
RESORT_TIME_ZONE = "America/Denver"

ATTRIBUTION = "Data provided by Big Sky Resort"
