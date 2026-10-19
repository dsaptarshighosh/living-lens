"""Adapter for a locally supplied, trusted scikit-learn artifact from the provided notebook."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ARTIFACT=ROOT/'model.joblib'
METADATA=ROOT/'model_metadata.json'
_model=None; _metadata=None; _error=None

def load():
    global _model,_metadata,_error
    if _model is not None: return _model,_metadata
    if not ARTIFACT.is_file() or not METADATA.is_file():
        _error='No fitted model artifact or training CSV was included.'; return None,None
    try:
        import joblib
        meta=json.loads(METADATA.read_text(encoding='utf-8'))
        if not meta.get('feature_columns') or not meta.get('animal_names') or not meta.get('behaviours'):
            raise ValueError('Metadata must declare feature_columns, animal_names, and behaviours.')
        _model=joblib.load(ARTIFACT); _metadata=meta; _error=None
    except Exception as e: _error=f'Model could not be loaded: {e}'
    return _model,_metadata

def status():
    model,meta=load()
    result={'ready':model is not None,'reason':_error,'target':'Hazard_Probability','animal_names':[],'behaviours':[]}
    if model is not None:
        result.update(target=meta.get('target','Hazard_Probability'),animal_names=meta['animal_names'],behaviours=meta['behaviours'])
    return result

def predict(animal,behaviour,intensity,abnormality,duration):
    model,meta=load()
    if model is None: raise RuntimeError(_error or 'Model unavailable')
    if animal not in meta['animal_names'] or behaviour not in meta['behaviours']:
        raise ValueError('Animal or behaviour category is not represented in the training data.')
    import pandas as pd
    values={'Intensity':float(intensity),'Abnormality_Percentage':float(abnormality),'Duration_Minutes':float(duration)}
    values.update({f'Animal_Name_{x}':float(x==animal) for x in meta['animal_names']})
    values.update({f'Behaviour_{x}':float(x==behaviour) for x in meta['behaviours']})
    row=pd.DataFrame([{name:values.get(name,0.0) for name in meta['feature_columns']}],columns=meta['feature_columns'])
    estimate=float(model.predict(row)[0])
    if not __import__('math').isfinite(estimate): raise ValueError('Model returned a non-finite estimate.')
    return estimate,str(meta.get('model_version','notebook-random-forest-200'))
