"""Reproduce the notebook's random forest fit once the original CSV is available."""
import argparse, json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(); parser.add_argument('csv',help='Path to zoo_sentinel_dataset_2800 (2) (1).csv'); args=parser.parse_args()
df=pd.read_csv(args.csv)
required={'Hazard_Probability','Animal_Name','Behaviour','Intensity','Abnormality_Percentage','Duration_Minutes'}
missing=required-set(df.columns)
if missing: raise SystemExit(f'Dataset is missing required columns: {sorted(missing)}')
y=df['Hazard_Probability']; x=pd.get_dummies(df.drop('Hazard_Probability',axis=1),columns=['Animal_Name','Behaviour']).astype(float)
x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.2,random_state=100)
model=RandomForestRegressor(n_estimators=200,random_state=100); model.fit(x_train,y_train)
pred=model.predict(x_test)
joblib.dump(model,HERE/'model.joblib')
metadata={'model_version':'notebook-random-forest-200','feature_columns':list(x.columns),'animal_names':sorted(map(str,df['Animal_Name'].dropna().unique())),'behaviours':sorted(map(str,df['Behaviour'].dropna().unique())),'target':'Hazard_Probability','notebook_test_r2':float(r2_score(y_test,pred)),'notebook_test_mse':float(mean_squared_error(y_test,pred))}
(HERE/'model_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
print(json.dumps({'rows':len(df),'test_r2':metadata['notebook_test_r2'],'test_mse':metadata['notebook_test_mse'],'artifact':str(HERE/'model.joblib')},indent=2))
