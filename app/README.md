# app/ — Flutter client (phase 3)

Empty on purpose. Nothing here has been built or verified: this container has
no Flutter SDK and no network route to pub.dev, so any Dart written here would
be unverified guesswork.

Scaffold it when you start phase 3:

    cd app && flutter create --org nl.bar371 --platforms android,ios .

Then structure per `PLAN.md` phase 3. Dependencies to add:

    shared_preferences          settings + install seed
    flutter_local_notifications daily notification
    timezone                    correct local fire time across DST
    http                        optional dataset refresh

`data/entries.json` gets wired in as a bundled asset via `pubspec.yaml`.
