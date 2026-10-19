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

The demo sign-in page shows the local demo credentials. They are public and only for testing on your own computer. **Never expose a demo-seeded app to the internet.**

For a real zoo setup, create an administrator account instead:

```powershell
python .\server.py --provision admin "Zoo Administrator" admin@example.test "use-a-unique-strong-password" "Example Zoo"
```

The server needs `LIVING_LENS_SECRET` set for either startup method. You can copy `.env.example` as a reference for the available settings; the app does not load `.env` files automatically.

## Set up the model

The model code follows the notebook: a 200-tree Random Forest using animal, behaviour, intensity, abnormality percentage, and observation duration. The dataset and trained model are deliberately not included here. If you have permission to use the dataset, install the model packages and train it locally:

```powershell
python -m pip install pandas scikit-learn joblib
python .\model\train_model.py "C:\path\to\zoo_sentinel_dataset_2800.csv"
```

The CSV needs these columns: `Animal_Name`, `Behaviour`, `Intensity`, `Abnormality_Percentage`, `Duration_Minutes`, and `Hazard_Probability`. Training creates `model/model.joblib` and `model/model_metadata.json` on your computer. Both files are ignored by Git. Without them, the upload form explains that predictions are unavailable.

The model is meant for experimentation with the supplied dataset, not operational hazard response. A high test score on one dataset does not establish real-world reliability. Joblib model files can execute code when loaded, so only train from data you trust.

## What’s in the app

- Zookeeper sign-in, observation entry, model estimate, and personal observation history.
- Admin sign-in and zookeeper account management.
- Citizen registration, zoo alerts, and a zoo map.
- Six animal photos on the home page, with photographer and license credits.
- A small Python standard-library server backed by SQLite.

## Run the checks

```powershell
python -m unittest discover -s .\tests -v
```

The model-related tests need the local model files, so train the model first. The rest of the app uses Python’s standard library.

