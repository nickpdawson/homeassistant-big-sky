# homeassistant-big-sky
A custom component to expose lifts, trails, weather, parking, and more from Big Sky resort to Home Assistant
# Big Sky Resort Home Assistant Integration

This Home Assistant custom component integrates Big Sky Resort data into your smart home setup. It pulls resort information from an XML feed, providing live data on lift and trail statuses, snowmaking, weather, and more for Big Sky Resort.

## Features
- Separate or aggregated entities for lifts and trails, depending on configuration.
- Binary sensors for resort and snowmaking statuses.
- Current weather and forecast sensors.
- Configurable update intervals (recommended polling interval: **1 hour** to avoid excessive load on the data source).

## Installation

1. **Download the Repository**:
   Clone this repository or download it as a ZIP file and place the `big_sky` folder in your Home Assistant `custom_components` directory.

   ```bash
   git clone https://github.com/nickpdawson/homeassistant-big-sky.git
Enable the Integration in Home Assistant:
Restart Home Assistant to detect the new integration.
Go to Settings > Devices & Services > Integrations and click Add Integration.
Search for "Big Sky Resort" and select it.
Follow the setup prompts to configure your XML feed URL, entity preferences, and update interval.
Configuration Options
XML Feed URL: The source URL for Big Sky Resort data.
Update Interval: How frequently to poll the feed for updates. (Recommended: 1 hour to be a good citizen and avoid excessive requests)
Separate Lift and Trail Entities: Choose whether to create individual entities for each lift and trail or to aggregate statuses in a single entity.
Example YAML Configuration
If you'd prefer YAML configuration, add the following to your configuration.yaml:

yaml
Copy code
big_sky:
  feed_url: "https://example.com/your-feed-url"
  update_interval: 60  # in minutes
  create_lift_entities: true
  create_run_entities: true
Development and Contributions
Pull requests are welcome! Please submit issues or feature requests if you have ideas or improvements.

Acknowledgments
Data provided by Big Sky Resort.
Special thanks to Home Assistant's community for supporting open integrations.
vbnet
Copy code

This `README.md` includes an overview, installation instructions, configuration optio
