# HA Activity Bridge

*HUAWEI Health activity data in Home Assistant, through the official Health Kit API.*

Custom integration that reads your **HUAWEI Health** data (watch, band, scale) through Huawei's
**official Health Kit cloud API** and brings it into Home Assistant:

- one sensor per metric with the latest daily value;
- the **whole history** imported into Home Assistant's long-term statistics
  (`huawei_health_kit:<user>_<metric>`), usable in statistics graphs and the energy-style cards.

Nothing to install on the phone, and the HUAWEI Health app keeps working as usual: the
integration only reads what the app already syncs to Huawei's cloud, with your consent (OAuth).

> **Status: early development (0.1.0), not tested against the live API yet.**
> It needs a Huawei Developers app with Health Kit access, see *Setup*.

## Why another Huawei Health integration?

Other community integrations read the HUAWEI Health app's private cloud protocol by imitating the
app. This one only uses the documented, official API:

| | This integration | App-imitating integrations |
|---|---|---|
| API | official Health Kit REST API | private, reverse engineered |
| Huawei terms of service | compliant | grey area |
| Phone app session | untouched | shares the app's token |
| History in long-term statistics | yes, from 2014 | no |
| Setup | needs your own Huawei Developers app | browser login only |

## Data

> [!WARNING]
> **Huawei refuses health data to individual developers.** With an individual HUAWEI Developers
> account, Huawei only grants the *Activity* category (steps, distance, calories). Weight, heart
> rate, sleep, stress, SpO2 and body temperature are reserved for **enterprise** accounts (a
> registered company): the author's application was rejected for exactly this reason
> ("Individual developers cannot apply for health-related data"). The code for these categories
> is kept, but untested, for anyone who has an enterprise account. To get this data into Home
> Assistant as an individual, you need another route, such as a phone app that copies
> HUAWEI Health data to another service.

| Category | Sensors | Health Kit scope | Individual account |
|---|---|---|---|
| Activity | steps, distance, calories (daily totals) | `step.read`, `distance.read`, `calories.read` | yes |
| Weight | weight (daily mean/min/max) | `heightweight.read` | no (enterprise only) |
| Heart rate | heart rate, resting heart rate | `heartrate.read` | no (enterprise only) |
| Sleep | total, deep, light, REM, awake (min), wake-ups | `sleep.read` | no (enterprise only) |
| Stress | stress score | `stress.read` | no (enterprise only) |
| SpO2 | blood oxygen | `oxygensaturation.read` | no (enterprise only) |
| Body temperature | body temperature | `bodytemperature.read` | no (enterprise only) |

Values are read every 30 minutes (last 7 days, to catch late syncs from the watch). At first
start, the history is backfilled in the background, 30 days per request.

## Setup

Each user uses **their own** Huawei Developers app (like the Withings or Google integrations):
the app is only used by you, and Health Kit's *test permission* allows up to 100 users.

1. **HUAWEI Developers account**: sign in at <https://developer.huawei.com> with the HUAWEI ID of
   your HUAWEI Health app and complete the identity verification (individual).
2. **Project and app**: in *AppGallery Connect*, create a project and an app, then note the
   **App ID** (client ID) and **App secret** (client secret). The app name must not contain
   "Huawei" (Health Kit rejects the application otherwise).
3. **HUAWEI ID / OAuth**: enable the HUAWEI ID service and add the redirect URL
   `https://my.home-assistant.io/redirect/oauth`.
4. **Health Kit**: *Console → App services → Health Kit → Apply for Health Kit*. With an individual
   account, tick only the steps, distance and calories read permissions; any health-data box
   gets the whole application rejected. Give **one scenario and purpose per permission** (none
   blank, no permission sharing a scenario), and leave unticked: authorization without login,
   HarmonyOS Connect device information, nutrition data, personal score reports and fitness
   capabilities. The review takes about 10 to 15 working days. Wait 24 h after approval.
5. **HUAWEI Health app**: allow data sharing with your app when asked (or in *Me → Privacy
   management → Data sharing and authorization*).
6. **Home Assistant**: install with HACS (custom repository
   `https://github.com/ucsky/ha-activity-bridge`, category *Integration*), restart, then
   *Settings → Devices & services → Add integration → HA Activity Bridge*. Enter the App
   ID and App secret, pick the categories, and sign in with your HUAWEI ID.

## Testing against the live API (developers)

`tools/probe.py` checks the Health Kit API outside Home Assistant (standard library only):

```bash
python3 -I tools/probe.py --cred /path/to/cred.yml --categories activity
```

`cred.yml` holds `- ClientID: <App ID>` and `  Secret: <App secret>`. Open the printed URL, sign in,
then copy the `https://my.home-assistant.io/redirect/oauth?code=...` URL from the address bar
(without clicking *Open link*) and paste it. The script tests the token exchange and refresh, calls
`dailyPolymerize` for each data type and writes the redacted responses (no token, user or device
identifier) to `probe-output/<timestamp>/`. `--categories ""` tests the HUAWEI ID sign-in only
(token exchange and refresh), which works before the Health Kit application is approved.

## Privacy

The integration runs entirely in your Home Assistant: data goes from Huawei's cloud to your
instance only. Nothing is sent to the author or any third party. Tokens are stored in Home
Assistant's config entry; the daily history in `.storage/huawei_health_kit.<entry_id>`.
See [docs/privacy-policy.md](docs/privacy-policy.md).

## License

MIT. Not affiliated with or endorsed by Huawei.
