# Privacy Policy: Huawei Health (Health Kit) for Home Assistant

*Last updated: 2026-11-02*

This policy describes how the open-source software "Huawei Health (Health Kit) for Home Assistant"
(the "Integration", <https://github.com/ucsky/ha-huawei-health-kit>) handles your data.

## 1. Who processes your data

The Integration is software that **you** install and run on **your own** Home Assistant
instance. The author does not operate any server, does not receive, store or process any of your
data, and has no access to your Home Assistant instance.

## 2. Data read

With your explicit consent, given on HUAWEI's authorization screen (OAuth 2.0), the Integration
reads the following HUAWEI Health data, only for the categories you select: daily activity (steps,
distance, calories), weight, heart rate and resting heart rate, sleep, stress, blood oxygen
saturation (SpO2) and body temperature. It never writes or deletes data in HUAWEI Health.

## 3. Purpose

The data is used only to display it in your own Home Assistant instance (sensors, graphs and
long-term statistics) for your personal use.

## 4. Storage and transfer

- Data is transferred directly from HUAWEI's Health Kit servers to your Home Assistant instance,
  over HTTPS.
- It is stored only on your Home Assistant instance: access and refresh tokens in its
  configuration, daily values in its storage and recorder database.
- No data is shared with, sold to, or transferred to the author or any third party.

## 5. Retention and deletion

Data stays on your Home Assistant instance until you delete it. Removing the Integration deletes
its tokens and stored daily values; long-term statistics can be deleted from Home Assistant's
*Developer tools → Statistics*. You can revoke the access at any time in your HUAWEI ID account
(*Privacy center → Apps*) or in the HUAWEI Health app.

## 6. Your rights

As the author holds none of your data, requests about data held by HUAWEI should be sent to HUAWEI
(see HUAWEI's privacy statement). Questions about the Integration:
<https://github.com/ucsky/ha-huawei-health-kit/issues>.

## 7. Changes

Changes to this policy are published in this repository, with the date above updated.
