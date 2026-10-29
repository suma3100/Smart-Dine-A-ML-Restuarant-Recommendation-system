# SmartDine

A group restaurant recommendation system that combines cuisine preferences, budgets and neighborhoods to rank restaurants in Bangalore.

**[Try the live app](https://smart-dine.streamlit.app/)**

## Main Features

- Build a group profile from individual member preferences.
- Filter by cuisine, neighborhood, rating, budget, booking and online ordering.
- Get ranked recommendations with match scores and explanations.
- See one best-matching branch per restaurant name, without repeated names.

## Tech Stack

Python, Streamlit, scikit-learn, pandas and NumPy. An optional FastAPI service provides a separate web dashboard and API.

## Run Locally

Run these commands in PowerShell with Python 3.12 installed:

```powershell
git clone https://github.com/suma3100/Smart-Dine-A-ML-Restuarant-Recommendation-system.git smart-dine-main
cd smart-dine-main
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

Open [localhost:8502](http://localhost:8502/). The Streamlit app uses the included model and processed data directly, so no separate API server is required.

For the optional dashboard and API, run this in another terminal from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn SmartDine.src.serving:app --host 127.0.0.1 --port 8001
```

Open [the dashboard](http://127.0.0.1:8001/) or [API documentation](http://127.0.0.1:8001/docs).

## Data and Model

The project includes 12,499 processed restaurant records and 100 synthetic groups containing 401 members. Linear Regression was selected through validation and evaluated on separate test groups using the same restaurant catalogue.

| Test metric | Result |
| --- | --- |
| MAE | 0.02399 |
| RMSE | 0.03007 |
| R² | 0.80731 |

These results measure agreement with a constructed preference score using synthetic groups, rather than real-user satisfaction. Displayed scores are ranking indices, not probabilities.

## Important Notes

- Budgets represent INR for two people.
- Dietary compatibility is an unverified heuristic. Confirm menus and preparation with the restaurant.
- Time and day are display context and do not affect the trained model.
- Filters remain strict. If too few restaurants match, adjust the filters explicitly.
- The original raw dataset is absent, and its source version and license remain unverified. The included artifacts support running the app, but full raw-data regeneration requires the original input.

See [PROJECT_AUDIT.md](PROJECT_AUDIT.md) for pipeline details and [model metadata](SmartDine/models/model_metadata.json) for evaluation evidence.
