# Privacy Policy: Huawei Health (Health Kit) for Home Assistant

*Last updated: 2026-11-08*

This policy describes how the open-source software "Huawei Health (Health Kit) for Home Assistant"
(the "Integration", <https://github.com/ucsky/ha-huawei-health-kit>) handles your data.

## 1. Who processes your data

The Integration is software that **you** install and run on **your own** Home Assistant
instance. The author (an individual developer) does not operate any server, does not receive,
store or process any of your data, and has no access to your Home Assistant instance. The
Integration contains no analytics, telemetry, advertising or tracking code.

Because the data is processed only on your own device, for your own personal use, you remain in
control of it at all times.

## 2. Data read

With your **explicit consent**, given on HUAWEI's authorization screen (OAuth 2.0), the
Integration reads only the data you select during setup:

- **Account identifier:** the user identifier of your HUAWEI ID (OpenID `sub`), used only to tell
  two HUAWEI accounts apart in the same Home Assistant instance. Your name, e-mail address and
  phone number are not read.
- **Health and fitness data from HUAWEI Health**, per selected category: daily activity (steps,
  distance, calories), weight, heart rate and resting heart rate, sleep, stress, blood oxygen
  saturation (SpO2) and body temperature.

The Integration only reads data. It never writes, modifies or deletes data in HUAWEI Health.

## 3. Purpose and legal basis

The data is used only to display it in your own Home Assistant instance (sensors, graphs and
long-term statistics) for your personal, non-commercial use.

Health data is a special category of personal data. It is read only on the basis of your
explicit consent (EU General Data Protection Regulation, Art. 6(1)(a) and 9(2)(a)), which you
can withdraw at any time (see section 6).

Data obtained through HUAWEI Health Kit is **never**:

- used for advertising, marketing or profiling;
- sold, rented or shared with any third party;
- used to make decisions about insurance, credit, employment or eligibility;
- used for any purpose other than the one described above.

## 4. Storage, transfer and security

- Data is transferred directly from HUAWEI's Health Kit servers to your Home Assistant instance,
  over encrypted connections (HTTPS).
- It is stored only on your Home Assistant instance: access and refresh tokens in its
  configuration, daily values in its storage (`.storage/huawei_health_kit.<entry_id>`) and in its
  recorder database (long-term statistics).
- No data is transferred to the author or to any third party.
- You are responsible for the security of your Home Assistant instance (access control,
  updates, backups). Backups of your instance contain the data and tokens described above.

## 5. Retention and deletion

Data stays on your Home Assistant instance until you delete it:

- removing the Integration deletes its tokens and stored daily values;
- long-term statistics can be deleted in Home Assistant (*Developer tools → Statistics*).

## 6. Withdrawing consent

You can withdraw the Integration's access at any time, without affecting data already displayed:

- in the HUAWEI Health app (*Me → Privacy management → Data sharing and authorization*);
- in your HUAWEI ID account settings (authorized apps);
- or by removing the Integration from Home Assistant.

## 7. Your rights

As the author holds none of your data, your rights of access, rectification, erasure,
restriction, portability and objection regarding data held by HUAWEI are exercised with HUAWEI
(see HUAWEI's privacy statement). You also have the right to lodge a complaint with a
supervisory authority, for example the CNIL in France (<https://www.cnil.fr>).

## 8. Children

The Integration is not intended for children under 16. Do not connect the HUAWEI account of a
child under 16 without the consent of their parent or guardian.

## 9. Changes and contact

Changes to this policy are published in this repository, with the date above updated; the full
history is available in the repository's commit log.

Questions about the Integration or this policy:
<https://github.com/ucsky/ha-huawei-health-kit/issues>.

*HUAWEI and HUAWEI Health are trademarks of Huawei Technologies Co., Ltd. The Integration is not
affiliated with or endorsed by HUAWEI.*
