# TODO

- [x] Huawei Developers account verified (individual).
- [x] Health Service Kit application of 2026-11-07 (steps, distance, calories, height/weight read)
      **rejected on 2026-11-09**: "Individual developers cannot apply for health-related data",
      and each permission needs its own scenario and purpose. Health data is enterprise-only:
      out of reach for this project (no company will be created for it).
- [ ] Health Kit application resubmitted on 2026-11-10: steps, distance and calories read only,
      one scenario/purpose per permission, application material v2 (activity only). Waiting for
      the review (about 10 working days).
- [x] HUAWEI ID OAuth checked live on 2026-11-08 (`tools/probe.py --categories ""`): token exchange
      OK, `access_type=offline` gives a refresh token, id_token has `sub`, access token valid 3600 s,
      refresh OK but returns no new refresh token (Home Assistant keeps the old one). The
      authorization code expires within seconds: the redirect must not wait for a click.
- [ ] First live test of the Health Kit scopes with `tools/probe.py` once the application is approved (`--categories activity`).
- [ ] Check real `dailyPolymerize` responses for each data type: field names (SpO2
      `saturation_avg`, stress/resting HR `avg`), units, several sample points per day.
- [ ] Sleep: check which day a night is attributed to (night ending on day D?) and whether
      `activityRecords?activityType=65` gives better per-night data.
- [ ] HTTP 403 for a whole request vs per data type: confirm the per-type fallback.
- [x] Publish the privacy policy and user agreement at public URLs (needed in the Health Kit
      application): GitHub Pages or make the repo public.
- [ ] Contact e-mail in the privacy policy and user agreement (Huawei may ask for one): create a
      dedicated address (e.g. a new Gmail account), then add it to both documents (section 9 /
      item 12) next to the GitHub issues link.
- [ ] Options flow (change categories, history start date), diagnostics, repair issue when data
      sharing is not enabled in the HUAWEI Health app.
- [x] Before making the repo public: enable GitHub secret scanning + push protection (not available on private personal repos), re-run `trufflehog git file://. --no-update` on the whole history.
- [ ] Brand icon, tests with pytest-homeassistant-custom-component, first release, HACS.
