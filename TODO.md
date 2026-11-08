# TODO

- [x] Huawei Developers account verified (individual).
- [ ] Health Service Kit test permission granted: applied 2026-11-07 (Server-to-Server app, steps,
      distance, calories, height/weight read), status "To be reviewed" (about 10 working days).
      Check that the application material (docs list) is attached; the upload failed with
      "Internal service exception".
- [ ] First live test with `tools/probe.py` (see README): OAuth flow (scopes, `access_type=offline`, id_token `sub`), token refresh.
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
