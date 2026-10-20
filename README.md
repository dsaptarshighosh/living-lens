# Living Lens

I made Living Lens to explore whether changes in animal behaviour could help people notice possible environmental risks sooner. A zookeeper can record an observation and, once the model is set up, get an experimental hazard-probability estimate. Zookeepers can see their own observation history; zoo administrators manage keeper accounts.

This is a prototype, not an official warning system. The model's estimate is not a confirmed threat or a scientifically validated prediction.

## Run it on your computer

You'll need Python 3.9 or newer. In PowerShell, open this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:LIVING_LENS_SECRET = (& python -c "import secrets; print(secrets.token_hex(32))")
python .\server.py
```

Then visit <http://127.0.0.1:8000>. The app creates a local SQLite database the first time it runs. Keep your secret private; don't reuse it for a public deployment.

To try the demo accounts, keep that terminal open, stop the server with Ctrl+C, then run:

```powershell
python .\seed_demo.py
python .\server.py
```

The local demo sign-in page used to show fixed demo credentials; the sign-in page no longer displays or fills any credentials. **Do not expose a demo-seeded local app to the internet.**

For a real zoo setup, create an administrator account instead:

```powershell
python .\server.py --provision admin "Zoo Administrator" admin@example.test "use-a-unique-strong-password" "Example Zoo"
```

The server needs `LIVING_LENS_SECRET` set for either startup method. You can copy `.env.example` as a reference for the available settings; the app does not load `.env` files automatically.

## Deploy a public demo

The repository includes a Render Blueprint in `render.yaml`. In Render, create a new Blueprint and connect this GitHub repository. When asked for the unsynced values, enter separate demo account emails and passwords for `LIVING_LENS_ADMIN_EMAIL`, `LIVING_LENS_ADMIN_PASSWORD`, `LIVING_LENS_KEEPER_EMAIL`, and `LIVING_LENS_KEEPER_PASSWORD`. Use passwords of at least 16 characters. Render generates `LIVING_LENS_SECRET` for the app. Keep the account passwords in Render's environment settings, not in GitHub.

The model artifact and its metadata are included in this public repository so the hosted app can make Hazard Probability estimates. The training dataset and local SQLite database are not included. Render's free service may sleep while idle, and its local database is temporary: accounts and observations can reset after a redeploy or restart. Create only fake demo observations, and give judges the demo zookeeper sign-in details separately.

## Set up the model

The model code follows the notebook: a 200-tree Random Forest using animal, behaviour, intensity, abnormality percentage, and observation duration. The trained model is included for the hosted demo; the training dataset is not. If you have permission to use the dataset and want to retrain it, install the model packages and run:

```powershell
python -m pip install pandas scikit-learn joblib
python .\model\train_model.py "C:\path\to\zoo_sentinel_dataset_2800.csv"
```

The CSV needs these columns: `Animal_Name`, `Behaviour`, `Intensity`, `Abnormality_Percentage`, `Duration_Minutes`, and `Hazard_Probability`. Training creates `model/model.joblib` and `model/model_metadata.json` on your computer. Do not publish the dataset unless you have permission to share it.

The model is meant for experimentation with the supplied dataset, not operational hazard response. A high test score on one dataset does not establish real-world reliability. Joblib model files can execute code when loaded, so only train from data you trust.

## What’s in the app

- Zookeeper sign-in, observation entry, model estimate, and personal observation history.
- Admin sign-in and zookeeper account management.
- Citizen registration requires choosing a nearest zoo from the supported list. Citizens can opt in to email and/or SMS alerts at registration and update those preferences later.
- Zookeepers choose the zoo/location for each report. Every new report is delivered only to citizens subscribed to that zoo and opted in to a notification channel.
- Email delivery uses optional SMTP settings; SMS delivery uses optional Twilio settings. Set provider credentials in the deployment environment (never in GitHub) to enable delivery. Until configured, citizens can still view their zoo's alerts in the portal.
- Six animal photos on the home page, with photographer and license credits.
- A small Python standard-library server backed by SQLite.

## Run the checks

```powershell
python -m unittest discover -s .\tests -v
```

The model-related tests need the local model files, so train the model first. The rest of the app uses Python’s standard library.

## Email and SMS notifications

Notification channels are opt-in. Add provider settings from `.env.example` to the Render service environment to enable delivery: SMTP host/from (plus username/password when required) for email, or Twilio account SID/auth token/from-number for SMS. Keep credentials private. Report updates are independent of hazard alerts. Alerts are created only when `LIVING_LENS_ALERT_THRESHOLD` is configured and the model estimate reaches it; the threshold is unset by default. Do not treat these experimental estimates as official hazard warnings.

