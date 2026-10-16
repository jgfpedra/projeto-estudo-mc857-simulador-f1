# train_multi_context.py
import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent

# Auto-detect project virtualenv if running outside venv and dependencies missing
VENV_DIR = PROJECT_ROOT / "backend" / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
if sys.prefix != str(VENV_DIR) and VENV_PYTHON.exists():
    try:
        import fastf1
    except ImportError:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

import fastf1 as ff1
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib

CACHE_DIR = PROJECT_ROOT / 'backend' / 'cache'
DEFAULT_DATA_PATH = MODEL_DIR / 'multi_context_data.npz'
DEFAULT_REF_PATH = MODEL_DIR / 'reference_path.csv'
DEFAULT_MAPPINGS_PATH = MODEL_DIR / 'mappings.pkl'

RACES = [
    # (2021, 'British Grand Prix', 'Q'),
    # (2021, 'Monaco Grand Prix', 'Q'),
    # (2021, 'Italian Grand Prix', 'Q'),
    # (2022, 'Monaco Grand Prix', 'Q'),
    # (2022, 'Dutch Grand Prix', 'Q'),
    
    (2022, 'São Paulo Grand Prix', 'R'),
    (2023, 'São Paulo Grand Prix', 'R'),
    (2024, 'São Paulo Grand Prix', 'R'),
    (2025, 'São Paulo Grand Prix', 'R'),
    
]
DRIVERS = ['HAM', 'VER', 'LEC', 'NOR', 'RUS']

def process_lap(lap, driver_id, track_id):
    tel = lap.get_telemetry()
    tel['Time'] = (tel['Date'] - tel['Date'].iloc[0]).dt.total_seconds()
    speed_kmh = tel['Speed'].values
    speed_ms = speed_kmh / 3.6
    dt = np.diff(tel['Time'].values, prepend=0)
    tel['Distance'] = np.cumsum(speed_ms * dt)
    tel['Acceleration'] = np.gradient(speed_ms, tel['Time'])
    tel['RPM_dot'] = np.gradient(tel['RPM'].values, tel['Time'].values)
    tel['Brake'] = tel['Brake'].astype(float)

    x = tel['X'].values / 10.0
    y = tel['Y'].values / 10.0
    dx = np.diff(x, prepend=x[0])
    dy = np.diff(y, prepend=y[0])
    heading = np.arctan2(dy, dx)
    heading_smooth = pd.Series(heading).rolling(5, center=True, min_periods=1).mean().values
    yaw_rate = np.gradient(heading_smooth, tel['Time'].values)
    v_safe = np.maximum(speed_ms, 1.0)
    curvature = yaw_rate / v_safe
    tel['Steering'] = np.clip(1000.0 * curvature, -180, 180)
    tel['Curvature'] = curvature

    feature_cols = ['Speed', 'RPM', 'nGear', 'DRS', 'Distance', 'Time', 'Acceleration', 'RPM_dot', 'Curvature']
    target_cols = ['Throttle', 'Brake', 'Steering']
    
    tel['DriverID'] = driver_id
    tel['TrackID'] = track_id
    
    tel['TyreLife'] = float(lap['TyreLife']) if pd.notna(lap['TyreLife']) else 0.0
    tel['Fuel'] = 100.0 - (tel['Time'] / tel['Time'].iloc[-1]) * 30.0 
    tel['CompoundID'] = str(lap['Compound'])

    return tel[['X', 'Y', 'DriverID', 'TrackID', 'TyreLife', 'Fuel', 'CompoundID'] + feature_cols + target_cols]

def collect_and_prepare_dataset(cache_dir=None, save_dir=None):
    c_dir = Path(cache_dir or CACHE_DIR)
    c_dir.mkdir(parents=True, exist_ok=True)
    ff1.Cache.enable_cache(str(c_dir))

    s_dir = Path(save_dir or MODEL_DIR)
    s_dir.mkdir(parents=True, exist_ok=True)

    all_data = []
    driver_map = {}
    track_map = {}
    compound_map = {}

    for year, gp, sess_type in RACES:
        print(f"Baixando {gp} {year}...")
        try:
            session = ff1.get_session(year, gp, sess_type)
            session.load()
            
            if gp not in track_map:
                track_map[gp] = len(track_map)
            track_id = track_map[gp]
            
            available_drivers = session.results['Abbreviation'].tolist()
            
            for drv in DRIVERS:
                if drv not in available_drivers:
                    print(f"  - Piloto {drv} não encontrado em {gp}. Pulando.")
                    continue
                    
                if drv not in driver_map:
                    driver_map[drv] = len(driver_map)
                    
                laps = session.laps.pick_driver(drv)
                if laps.empty:
                    continue
                    
                fastest_laps = laps.sort_values('LapTime').head(3)
                
                for _, lap in fastest_laps.iterrows():
                    compound = str(lap['Compound'])
                    if compound not in compound_map:
                        compound_map[compound] = len(compound_map)
                    
                    try:
                        tel = process_lap(lap, driver_map[drv], track_id)
                        tel['CompoundID'] = compound_map[compound]
                        all_data.append(tel)
                        print(f"  - Processado: {drv} em {gp} ({compound})")
                    except Exception as e:
                        print(f"  - Erro ao processar volta de {drv}: {e}")
                        
        except Exception as e:
            print(f"Erro ao carregar {gp}: {e}")

    if not all_data:
        raise ValueError("Nenhum dado foi coletado! Verifique se o FastF1 está baixando as telemetrias corretamente.")

    df = pd.concat(all_data, ignore_index=True)

    feature_cols = ['Speed', 'RPM', 'nGear', 'DRS', 'Distance', 'Time', 'Acceleration', 'RPM_dot', 'Curvature']
    context_num_cols = ['TyreLife', 'Fuel']
    context_cat_cols = ['DriverID', 'TrackID', 'CompoundID']
    target_cols = ['Throttle', 'Brake', 'Steering']

    mask = ~np.isnan(df[feature_cols].values).any(axis=1) & ~np.isnan(df[target_cols].values).any(axis=1)
    df = df[mask]

    ref_df = df[['X', 'Y']].drop_duplicates().reset_index(drop=True)
    ref_path = s_dir / 'reference_path.csv'
    ref_df.to_csv(str(ref_path), index=False)
    print(f"Trajetória de referência salva em: {ref_path}")

    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    scaler_ctx_num = StandardScaler()

    X_scaled = scaler_X.fit_transform(df[feature_cols].values)
    y_scaled = scaler_y.fit_transform(df[target_cols].values)
    ctx_num_scaled = scaler_ctx_num.fit_transform(df[context_num_cols].values)
    ctx_cat = df[context_cat_cols].values.astype(np.int32)

    npz_path = s_dir / 'multi_context_data.npz'
    np.savez(str(npz_path), 
             X=X_scaled, 
             y=y_scaled, 
             ctx_num=ctx_num_scaled, 
             ctx_cat=ctx_cat,
             X_raw=df[feature_cols].values,
             positions=df[['X','Y']].values)

    joblib.dump(scaler_X, str(s_dir / 'scaler_X_multi.pkl'))
    joblib.dump(scaler_y, str(s_dir / 'scaler_y_multi.pkl'))
    joblib.dump(scaler_ctx_num, str(s_dir / 'scaler_ctx_num.pkl'))
    joblib.dump({'drivers': driver_map, 'tracks': track_map, 'compounds': compound_map}, str(s_dir / 'mappings.pkl'))

    print(f"Dataset salvo com sucesso em: {npz_path}! Amostras: {len(df)}")
    print(f"Mapeamentos: {driver_map}, {track_map}, {compound_map}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Coleta e pré-processamento de telemetria FastF1")
    parser.add_argument("--save-dir", type=str, default=str(MODEL_DIR), help="Diretório onde salvar dataset e scalers")
    parser.add_argument("--cache-dir", type=str, default=str(CACHE_DIR), help="Diretório de cache do FastF1")
    args = parser.parse_args()

    collect_and_prepare_dataset(cache_dir=args.cache_dir, save_dir=args.save_dir)