"""Constants for the Big Sky Resort integration."""

DOMAIN = "big_sky"
NAME = "Big Sky Resort"

CONF_FEED_URL = "feed_url"
CONF_CREATE_RUN_ENTITIES = "create_run_entities"
CONF_CREATE_LIFT_ENTITIES = "create_lift_entities"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_FEED_URL = "https://reportpal-cdn.resorts-interactive.com/mtnxml/162"
DEFAULT_UPDATE_INTERVAL = 15
MIN_UPDATE_INTERVAL = 1
MAX_UPDATE_INTERVAL = 60

ATTRIBUTION = "Data provided by Big Sky Resort"