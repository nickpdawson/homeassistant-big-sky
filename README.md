# Big Sky Resort for Home Assistant

A custom integration that reads the Big Sky Resort mountain report feed and
turns it into Home Assistant entities: lift and trail status, snow totals,
the daily forecast, terrain parks, parking and the shuttle.

The data comes from the public feed at
`https://reportpal-cdn.resorts-interactive.com/mtnxml/162`. This project is
not affiliated with Big Sky Resort.

Requires Home Assistant 2025.12 or newer. Tested on 2026.10.

## Install with HACS

1. In HACS, open the menu (three dots, top right) and pick **Custom repositories**.
2. Add `https://github.com/nickpdawson/homeassistant-big-sky` with type **Integration**.
3. Search HACS for **Big Sky Resort** and download it.
4. Restart Home Assistant.

To install by hand, copy `custom_components/big_sky` into your
`config/custom_components/` folder and restart.

## Setup

Go to **Settings > Devices & services > Add integration** and pick
**Big Sky Resort**. The form asks for:

- **Feed URL**: leave the default unless the resort moves its feed. Must be https.
- **Create an entity for each lift**: about 40 binary sensors.
- **Create an entity for each trail**: about 320 binary sensors.
- **Update interval**: 5 to 240 minutes, default 15. The resort updates the
  feed a few times a day, so 30 to 60 minutes is plenty.

Setup fetches the feed once and stops with an error if it cannot read it.
Only one entry is allowed. YAML setup is not supported.

## Options

**Settings > Devices & services > Big Sky Resort > Configure** changes the
same four settings. Saving reloads the integration. Turning lifts or trails
off removes those entities.

## Entities

All entities sit on one device, **Big Sky Resort**. Example ids for a new install:

| Entity | Example id | State |
| --- | --- | --- |
| Resort status | `binary_sensor.big_sky_resort_resort_status` | on when open |
| Snowmaking | `binary_sensor.big_sky_resort_snowmaking` | on when any trail has snowmaking |
| Each lift | `binary_sensor.big_sky_resort_lift_lone_peak_tram` | on when running |
| Each trail | `binary_sensor.big_sky_resort_trail_liberty_bowl` | on when open |
| Snow depth | `sensor.big_sky_resort_snow_depth` | base depth, in |
| Snowfall 24h, 48h, 72h, 7 days | `sensor.big_sky_resort_snowfall_24h` | in |
| Forecast high today | `sensor.big_sky_resort_forecast_high_today` | °F |
| Trails open | `sensor.big_sky_resort_trails_open` | count; attributes break it down by difficulty |
| Lifts open | `sensor.big_sky_resort_lifts_open` | count |
| Terrain parks open | `sensor.big_sky_resort_terrain_parks_open` | count; attributes list each park |
| Parking lots open | `sensor.big_sky_resort_parking_lots_open` | count; attributes list each lot |
| Tram | `sensor.big_sky_resort_tram` | Lone Peak Tram status text |
| Shuttle | `sensor.big_sky_resort_shuttle` | shuttle status text |
| Weather | `weather.big_sky_resort` | daily forecast |

The feed has no current temperature. The weather entity and the forecast
high sensor both show today's forecast high.

Get the forecast with the `weather.get_forecasts` action and `type: daily`.
Each day carries a real date, starting from the day the report was issued.

New lifts and trails get entities on the next fetch that lists them, with
no restart. Lifts and trails missing from the feed are not deleted; they
stay unavailable until the season changes back.

## Troubleshooting

Turn on debug logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.big_sky: debug
```

Or use **Download diagnostics** on the integration page. It includes the
settings and the last parsed feed.

- **Feed outage**: if the feed is down or returns something that is not the
  report, entities go unavailable and come back on the next good fetch.
  If it is down when Home Assistant starts, setup retries on its own.
- **Off season**: the feed keeps publishing in summer with everything
  closed, so lift and trail sensors read off and counts read 0. Snow values
  can be blank, which shows as unknown.
- **A lift or trail shows unavailable**: it is missing from the feed. The
  resort drops some lifts and trails between seasons, so the entity stays
  unavailable until the season changes back. If the resort renamed or
  removed it for good, delete the entity.

## Breaking changes in 2.0.0

- Minimum Home Assistant version is 2025.12.
- Unique ids now belong to the config entry and use the feed's lift and
  trail ids. Existing entities are migrated on first start, so entity ids,
  history and customizations carry over. A lift or trail that is no longer
  in the feed is not migrated.
- New installs get entity ids that start with the device name, for
  example `sensor.big_sky_resort_snow_depth` instead of
  `sensor.big_sky_snow_depth`.
- "Current Weather" is now "Forecast high today". It was always the forecast
  high, not a reading.
- Trail and resort status binary sensors use the opening device class, so
  they show Open and Closed instead of Running and Not running.
- Snowfall sensors use the precipitation device class. Counts are integers
  with a measurement state class, so they get long-term statistics.
- "Trails by Difficulty" is now "Trails open" and counts the new
  "advanced intermediate" difficulty. Trail attributes no longer include
  `uphill`, which the feed never sent.
- The update interval range is now 5 to 240 minutes. Entries set below 5
  minutes run at 5.
- Changes made in the options dialog now take effect. Before 2.0.0 they
  were saved but ignored.
- The YAML example in the old README never worked and has been removed.

## License

See [LICENSE](LICENSE).
