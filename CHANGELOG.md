# Changelog

## 0.1.0 (unreleased)

- First skeleton: OAuth2 with the user's Huawei Developers app (application credentials),
  choice of data categories, daily values through `sampleSet:dailyPolymerize`, sensors, history
  backfill and import into long-term statistics. Not yet tested against the live API.
- Removing the integration deletes its stored daily history.
- `tools/probe.py`: first live test of the API outside Home Assistant (redacted raw responses).
- Privacy policy and user agreement completed for the Health Service Kit application.
- Only *Activity* is selected by default. The other categories are marked "enterprise accounts
  only": Huawei refuses health data to individual developer accounts.
