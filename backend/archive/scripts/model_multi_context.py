# model_multi_context.py
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
        import tensorflow
    except ImportError:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Dropout, BatchNormalization, Embedding, Flatten, Concatenate
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
import numpy as np
import joblib

DEFAULT_DATA_PATH = MODEL_DIR / 'multi_context_data.npz'
DEFAULT_MAPPINGS_PATH = MODEL_DIR / 'mappings.pkl'
DEFAULT_MODEL_PATH = MODEL_DIR / 'multi_context_bc_model.keras'

def build_bc_model(telemetry_dim, ctx_num_dim, num_drivers, num_tracks, num_compounds):
    inp_telemetry = Input(shape=(telemetry_dim,), name='telemetry')
    inp_ctx_num = Input(shape=(ctx_num_dim,), name='ctx_numeric')
    inp_driver = Input(shape=(1,), name='driver_id', dtype='int32')
    inp_track = Input(shape=(1,), name='track_id', dtype='int32')
    inp_compound = Input(shape=(1,), name='compound_id', dtype='int32')

    emb_driver = Flatten()(Embedding(input_dim=num_drivers, output_dim=8, name='driver_emb')(inp_driver))
    emb_track = Flatten()(Embedding(input_dim=num_tracks, output_dim=8, name='track_emb')(inp_track))
    emb_compound = Flatten()(Embedding(input_dim=num_compounds, output_dim=4, name='compound_emb')(inp_compound))

    x = Concatenate()([inp_telemetry, inp_ctx_num, emb_driver, emb_track, emb_compound])
    x = Dense(256, activation='relu')(x)
    x = BatchNormalization()(x)
    x = Dropout(0.3)(x)
    x = Dense(128, activation='relu')(x)
    x = BatchNormalization()(x)
    x = Dropout(0.3)(x)
    x = Dense(64, activation='relu')(x)
    x = Dropout(0.2)(x)
    x = Dense(32, activation='relu')(x)

    out = Dense(3, activation='linear', name='actions')(x)

    model = Model(inputs=[inp_telemetry, inp_ctx_num, inp_driver, inp_track, inp_compound], outputs=out)
    model.compile(optimizer=Adam(0.0005), loss='mse', metrics=['mae'])
    return model

def train_bc_model(data_path=None, mappings_path=None, output_model_path=None, epochs=150, batch_size=256, patience=20, verbose=1):
    d_path = Path(data_path or DEFAULT_DATA_PATH)
    if not d_path.is_absolute() and not d_path.exists():
        if (MODEL_DIR / d_path).exists():
            d_path = MODEL_DIR / d_path
        elif (PROJECT_ROOT / d_path).exists():
            d_path = PROJECT_ROOT / d_path

    m_path = Path(mappings_path or DEFAULT_MAPPINGS_PATH)
    if not m_path.is_absolute() and not m_path.exists():
        if (MODEL_DIR / m_path).exists():
            m_path = MODEL_DIR / m_path
        elif (PROJECT_ROOT / m_path).exists():
            m_path = PROJECT_ROOT / m_path

    out_path = Path(output_model_path or DEFAULT_MODEL_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Carregando dados de: {d_path}")
    data = np.load(str(d_path))
    X_train = data['X']
    y_train = data['y']
    ctx_num_train = data['ctx_num']
    ctx_cat_train = data['ctx_cat']

    print(f"Carregando mapeamentos de: {m_path}")
    mappings = joblib.load(str(m_path))
    num_drivers = max(len(mappings.get('drivers', {})), 20)
    num_tracks = max(len(mappings.get('tracks', {})), 20)
    num_compounds = max(len(mappings.get('compounds', {})), 5)

    model = build_bc_model(
        telemetry_dim=X_train.shape[1],
        ctx_num_dim=ctx_num_train.shape[1],
        num_drivers=num_drivers,
        num_tracks=num_tracks,
        num_compounds=num_compounds
    )

    early_stop = EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True)

    print("Iniciando treinamento do modelo multi-contexto (Behavioral Cloning)...")
    model.fit(
        x={
            'telemetry': X_train,
            'ctx_numeric': ctx_num_train,
            'driver_id': ctx_cat_train[:, 0],
            'track_id': ctx_cat_train[:, 1],
            'compound_id': ctx_cat_train[:, 2]
        },
        y=y_train,
        validation_split=0.15,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop],
        verbose=verbose
    )

    model.save(str(out_path))
    print(f"Modelo salvo com sucesso em: {out_path}")
    return model

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Treinamento Behavioral Cloning (BC) Multi-Contexto")
    parser.add_argument("--epochs", type=int, default=150, help="Número de épocas (default: 150)")
    parser.add_argument("--batch-size", type=int, default=256, help="Tamanho do batch (default: 256)")
    parser.add_argument("--patience", type=int, default=20, help="Paciência do EarlyStopping (default: 20)")
    parser.add_argument("--data-path", type=str, default=str(DEFAULT_DATA_PATH), help="Caminho do arquivo .npz")
    parser.add_argument("--mappings-path", type=str, default=str(DEFAULT_MAPPINGS_PATH), help="Caminho do mappings.pkl")
    parser.add_argument("--output-model", type=str, default=str(DEFAULT_MODEL_PATH), help="Caminho para salvar o modelo .keras")
    args = parser.parse_args()

    train_bc_model(
        data_path=args.data_path,
        mappings_path=args.mappings_path,
        output_model_path=args.output_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        patience=args.patience
    )