"""MLflow tracking do projeto (FASE 0.7 v15).

Backend sqlite:///mlflow.db (raiz de backend/); artefatos em mlruns/.
Experimentos: dagger-solo, dagger-traffic, race-layer, overtaking, legacy-import.
Model Registry: os 3 checkpoints de DEPLOY com aliases race/quali/traffic
(`.venv/bin/python model_train/tracking.py --register-deploy` para (re)registrar).

Integração (0.8): os scripts chamam via guards `try: import tracking` — sem
mlflow instalado nada quebra (logging é best-effort, nunca bloqueia a corrida).
Logging só no processo principal (workers não importam mlflow).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
BACKEND = MODEL_DIR.parent
TRACKING_URI = f"sqlite:///{BACKEND / 'mlflow.db'}"
ARTIFACT_ROOT = str(BACKEND / 'mlruns')
REGISTRY_MODEL = "f1-bot"

EXPERIMENTS = ('dagger-solo', 'dagger-traffic', 'race-layer', 'overtaking',
               'legacy-import')

# DEPLOY fixo (PROJECT_STATE): alias -> (keras, obs_mode, experimento)
DEPLOY = {
    'race':   (MODEL_DIR / 'v10_dagger' / 'dagger_actor_best.keras', 'edge', 'dagger-solo'),
    'quali':  (MODEL_DIR / 'v11b_pace90' / 'dagger_actor_best.keras', 'edge', 'dagger-solo'),
    'traffic': (MODEL_DIR / 'v14_traffic' / 'dagger_actor_best_s1_n4.keras',
                'traffic', 'dagger-traffic'),
}


def _sanitize(name: str) -> str:
    """Métrica MLflow: [a-zA-Z0-9_./ -]; troca o resto por '_'."""
    return re.sub(r'[^a-zA-Z0-9_./ -]', '_', name)[:180]


def _mlflow():
    import mlflow
    mlflow.set_tracking_uri(TRACKING_URI)
    return mlflow


def start_run(experiment, params=None, tags=None):
    """Abre um run (contexto). Tags: status ∈ {deployed, research, discarded}."""
    mlflow = _mlflow()
    mlflow.set_experiment(experiment)
    run = mlflow.start_run(tags=tags or {})
    if params:
        mlflow.log_params({k: str(v) for k, v in params.items()})
    return run


def log_eval(protocol: str, per_track: dict):
    """Métricas de avaliação: voltas/eps por pista + tempo mediano.
    per_track: {pista: {laps, episodes, time_med, ...}}."""
    mlflow = _mlflow()
    mlflow.set_tag('protocol', protocol)
    tot_laps = sum(v.get('laps', 0) for v in per_track.values())
    tot_eps = sum(v.get('episodes', 0) for v in per_track.values())
    mlflow.log_metric('laps_total', tot_laps)
    mlflow.log_metric('episodes_total', tot_eps)
    for tr, v in per_track.items():
        base = f"eval_{_sanitize(tr)}"
        mlflow.log_metric(base + '_laps', v.get('laps', 0))
        if v.get('time_med') is not None:
            mlflow.log_metric(base + '_time_med', float(v['time_med']))
        for k in ('contacts_per_lap', 'post_launch'):
            if v.get(k) is not None:
                mlflow.log_metric(base + '_' + k, float(v[k]))


def log_race(metrics: dict):
    """Métricas de corrida (dicionário plano; chaves sanitizadas)."""
    mlflow = _mlflow()
    for k, v in metrics.items():
        if v is not None:
            mlflow.log_metric(_sanitize(k), float(v))


def log_checkpoint(path, alias=None, params=None):
    """Registra o .keras no Model Registry (com alias opcional) + loga o
    artefato no run ativo (se houver)."""
    mlflow = _mlflow()
    p = Path(path)
    if mlflow.active_run() is not None:
        mlflow.log_artifact(str(p), artifact_path='checkpoints')
        tags = {}
    # mlflow 3.x: register_model rejeita .keras cru; create_model_version
    # aceita source=arquivo. Best-effort — a resolução de deploy tem FALLBACK
    # para o caminho de arquivo (DEPLOY) se o registry falhar.
    client = mlflow.tracking.MlflowClient()
    try:
        try:
            client.create_registered_model(REGISTRY_MODEL)
        except Exception:
            pass  # já existe
        mv = client.create_model_version(name=REGISTRY_MODEL, source=str(p.resolve()))
        version = mv.version
    except Exception as e:
        print(f"[registry] AVISO: registro falhou ({type(e).__name__}) — "
              f"alias usa fallback de arquivo")
        return None
    if alias:
        client.set_registered_model_alias(REGISTRY_MODEL, alias, version)
    return version


def resolve_deploy(alias: str):
    """0.8: resolve checkpoint de deploy pelo alias do registry com FALLBACK
    para o caminho de arquivo (registry vazio/indisponível nunca quebra)."""
    try:
        mlflow = _mlflow()
        client = mlflow.tracking.MlflowClient()
        m = client.get_model_version_by_alias(REGISTRY_MODEL, alias)
        src = Path(m.source.replace("file://", ""))
        if src.exists():
            return src
    except Exception:
        pass
    return DEPLOY[alias][0]


def register_deploy():
    """(Re)registra os 3 checkpoints de deploy com aliases race/quali/traffic."""
    mlflow = _mlflow()
    for alias, (keras, _obs, exp) in DEPLOY.items():
        if not keras.exists():
            print(f"[registry] AUSENTE: {keras} — alias {alias} não registrado")
            continue
        with start_run(exp, params={'profile': alias},
                       tags={'status': 'deployed', 'profile': alias}):
            ver = log_checkpoint(keras, alias=alias)
        print(f"[registry] {alias} -> {keras.name} (versão {ver})")


if __name__ == '__main__':
    if '--register-deploy' in sys.argv:
        register_deploy()
    else:
        print("uso: tracking.py --register-deploy")
