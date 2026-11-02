# TODO

- [ ] Huawei Developers account verified (individual) and Health Kit test permission granted.
- [ ] First live test: OAuth flow (scopes, `access_type=offline`, id_token `sub`), token refresh.
- [ ] Check real `dailyPolymerize` responses for each data type: field names (SpO2
      `saturation_avg`, stress/resting HR `avg`), units, several sample points per day.
- [ ] Sleep: check which day a night is attributed to (night ending on day D?) and whether
      `activityRecords?activityType=65` gives better per-night data.
- [ ] HTTP 403 for a whole request vs per data type: confirm the per-type fallback.
- [ ] Publish the privacy policy and user agreement at public URLs (needed in the Health Kit
      application): GitHub Pages or make the repo public.
- [ ] Options flow (change categories, history start date), diagnostics, repair issue when data
      sharing is not enabled in the HUAWEI Health app.
- [ ] Before making the repo public: enable GitHub secret scanning + push protection (not available on private personal repos), re-run `trufflehog git file://. --no-update` on the whole history.
- [ ] Brand icon, tests with pytest-homeassistant-custom-component, first release, HACS.
