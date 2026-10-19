# Living Lens

Runnable local prototype built from the supplied Canva PDF interface frames and Colab notebook. The actual Figma file and source website project were not included, so this project does not claim an exact Figma match. The uploaded 2,800-row CSV has now been used to train the notebook's Random Forest model. The visual implementation follows the supplied 13-page Canva export: green gradient, deep teal panels, lime cards, and the visible landing, sign-in, registration, observation, history, map, account and guide views.

## Requirements

- Python 3.9 or newer.
- No packages are needed to run the app or use SQLite, registration, sign-in, account provisioning, and API endpoints.
- Model export needs `pandas`, `scikit-learn`, and `joblib` (see below).

## Start

In PowerShell, from this directory:

```powershell
$env:LIVING_LENS_SECRET = 'replace-this-with-a-long-random-secret'
python .\server.py
```

Open <http://127.0.0.1:8000>. The SQLite database is created at `living_lens.sqlite3` on first launch. Set `LIVING_LENS_DB` to choose another path. The API health route is `/api/health`.

Provision a zoo administrator and their zoo using a strong password:

```powershell
$env:LIVING_LENS_SECRET = 'same-long-random-secret'
python .\server.py --provision admin "Zoo Administrator" admin@example.test "replace-with-strong-password" "Example Zoo"
```

For a local demo only, seed these sample users after setting `LIVING_LENS_SECRET`:

```powershell
python .\seed_demo.py
```

| Role | Email | Password |
| --- | --- | --- |
| Zoo administrator | `demo.admin@livinglens.local` | `LensAdmin-2026!` |
| Zookeeper | `demo.keeper@livinglens.local` | `LensKeeper-2026!` |
| Citizen | `demo.citizen@livinglens.local` | `LensCitizen-2026!` |

These credentials are for local evaluation only. Change or remove them before exposing the app to other users. The demo accounts have no sample observations or alerts. A zookeeper can submit an observation when the trained model is ready.

The administrator can create zookeeper accounts from the Accounts view. Citizens register from the sign-in link and can choose a zoo and optionally enter coordinates. Registration is public only for citizen accounts; admin and zookeeper roles are provisioned by the zoo administrator. Sessions use signed, HttpOnly, SameSite cookies and passwords are stored with scrypt hashes.

## Model availability and export

The notebook trains a `RandomForestRegressor(n_estimators=200, random_state=100)` on an 80/20 split (`random_state=100`) and one-hot encodes `Animal_Name` and `Behaviour` with `pandas.get_dummies`. The private 2,800-row CSV and generated model artifacts are intentionally excluded from this public repository. The model must be trained locally from a compatible CSV before predictions are available. During local integration, the uploaded dataset's held-out test R² was 0.9395 and MSE was 21.5708; these differ from the notebook's saved result cells, so those cells correspond to a different dataset version.

The zookeeper observation form follows the notebook inputs: animal name, behaviour, intensity, abnormality percentage (derived from affected and total animal counts), and duration. Animal and behaviour choices come from the trained artifact metadata. The API runs inference before saving each observation and rejects the submission if inference fails.

To retrain with another compatible CSV, install the optional model dependencies and run:

```powershell
python -m pip install pandas scikit-learn joblib
python .\model\train_model.py "C:\path\to\zoo_sentinel_dataset_2800 (2) (1).csv"
```

This writes ignored local files `model/model.joblib` and `model/model_metadata.json`, using the notebook's model and train/test split. The backend loads the artifact once and only accepts animal and behaviour categories recorded in its metadata. Treat the model file as trusted code: joblib/pickle artifacts can execute code while loading. Review the dataset and artifact source before using them. Do not commit private datasets or model artifacts.

Set `LIVING_LENS_ALERT_THRESHOLD` only after confirming the target units and documenting an alert policy. No threshold is enabled by default. Alerts require both a genuine estimate above that configured threshold and actual coordinates. The estimate is not a calibrated probability for a named hazard. The current project does not analyze image/video uploads, weather, historical trends, or perform spatial-temporal clustering.

## Project files

- `server.py` - standard-library HTTP API, authentication, SQLite schema and role-scoped routes.
- `static/` - responsive frontend reflecting the available Canva PDF screens.
- `static/images/` - local animal photos for the homepage; each card links to the Commons source and its Creative Commons license.
- `model/inference.py` - one-time model loader and notebook-compatible one-hot encoding adapter.
- `model/train_model.py` - reproducible artifact export from the original dataset.
- The fitted model, model metadata, dataset CSV, and local database are excluded from Git; supply a compatible CSV and retrain locally to enable predictions.

## API summary

- `GET /api/health`, `GET /api/me`
- `POST /api/register` (citizen), `POST /api/login`, `POST /api/logout`
- `GET /api/observations`, `POST /api/observations` (zookeeper, own zoo)
- `GET /api/zookeepers`, `POST /api/zookeepers` (admin, own zoo)
- `GET /api/alerts`, `GET /api/map` (own zoo for zoo accounts and selected zoo for citizens)

JSON errors include an `error` field and appropriate HTTP status. Observation writes call model inference first; if the artifact is missing, unavailable or rejects an unseen category, no observation/prediction is stored.

## Checks

Run the offline core checks with:

```powershell
python -m unittest discover -s .\tests -v
```

The checks cover password hashing, relational persistence, zoo filtering, count constraints, model inference, and saving an observation with its model prediction. Model-inference tests require locally generated artifacts, so train the model before running the complete suite. The local health endpoint and zookeeper upload form were also verified in the browser.

## Current limitations

- The PDF is a rasterized Canva project export rather than the referenced Figma design; visual fidelity to the Figma source cannot be verified.
- There is no supplied source app, so the frontend is newly implemented to match the visible PDF frames and is not wired to an existing codebase.
- The map plots actual coordinates proportionally on a simple panel, with no third-party basemap or geocoding service. Weather UI is omitted because no real weather provider/configuration was supplied.
- Media attachment, alert acknowledgement, citizen distance-radius search, and an admin observation review screen were not implemented because the supplied frames do not give enough verified interaction/schema detail. These require the missing source design and product rules.

The offline core test suite passes in this workspace, including a real prediction from the trained artifact. The app should be run locally after setting a secret.
