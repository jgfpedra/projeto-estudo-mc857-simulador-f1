import os
import sys
import math
from collections import deque
from pathlib import Path

# Setup paths and PYTHONPATH first to prevent ModuleNotFoundError in main and spawned workers
MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent

# Auto-detect project virtualenv if running outside venv and dependencies missing
VENV_DIR = PROJECT_ROOT / "backend" / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
if sys.prefix != str(VENV_DIR) and VENV_PYTHON.exists():
    try:
        import gymnasium
        import tensorflow
    except ImportError:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

# Propagate PYTHONPATH to multiprocessing child workers (context="spawn")
current_ppath = os.environ.get("PYTHONPATH", "")
ppaths = [p for p in current_ppath.split(os.pathsep) if p]
for p in [str(PROJECT_ROOT), str(MODEL_DIR)]:
    if p not in ppaths:
        ppaths.insert(0, p)
os.environ["PYTHONPATH"] = os.pathsep.join(ppaths)

from backend.model_train.f1_env import F1MultiContextEnv
import numpy as np
import gymnasium as gym
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Embedding, Flatten, Concatenate
from tensorflow.keras.optimizers import Adam

DEFAULT_BC_PATH = MODEL_DIR / 'multi_context_bc_model.keras'
DEFAULT_REFERENCE_CSV = MODEL_DIR / 'reference_path.csv'
DEFAULT_ACTOR_PATH = MODEL_DIR / 'multi_context_rl_actor.keras'
DEFAULT_CRITIC_PATH = MODEL_DIR / 'multi_context_rl_critic.keras'

INT_KEYS = ('driver_id', 'track_id', 'compound_id')
LOG2PI = math.log(2.0 * math.pi)


def _tf_obs(obs):
    """dict de numpy -> dict de tensores (ids inteiros como int32, resto float32)."""
    return {k: tf.convert_to_tensor(v, dtype=tf.int32 if k in INT_KEYS else tf.float32)
            for k, v in obs.items()}


def _autoreset_is_next_step(vec_env):
    """gymnasium >= 1.0: após `done`, o PRÓXIMO step() só faz o reset (recompensa 0,
    a ação é ignorada). Essa transição é lixo e precisa ser mascarada no treino.
    gymnasium < 1.0 (0.29): o reset acontece no mesmo step (sem transição-lixo)."""
    mode = getattr(vec_env, "metadata", {}).get("autoreset_mode", None)
    if mode is not None:
        name = str(getattr(mode, "name", mode)).upper()
        if "NEXT" in name:
            return True
        if "SAME" in name:
            return False
        raise ValueError(f"autoreset_mode {mode} não suportado (use NEXT_STEP ou SAME_STEP)")
    return int(gym.__version__.split(".")[0]) >= 1


class MultiContextPPOAgent:
    def __init__(self, obs_spaces, act_dim, bc_path=None,
                 gamma=0.99, lam=0.95, clip=0.2,
                 lr=1e-4, critic_lr=3e-4, ent_coef=0.001, vf_coef=0.5,
                 max_grad=0.5, target_kl=0.03,
                 min_std=0.30,   # piso de exploração: 0.15 deixava a média
                                 # saturada em tanh(+/-0.99) sem prob. de
                                 # amostrar a ação oposta (freio) — a política
                                 # dava 'blips' de freio e voltava ao acelerador
                 init_log_std=None,            # default: log(0.6) por dimensão
                 init_actor_path=None, init_critic_path=None, init_std=None):
        self.gamma, self.lam, self.clip = gamma, lam, clip
        self.ent_coef, self.vf_coef = ent_coef, vf_coef
        self.max_grad, self.target_kl = max_grad, target_kl
        self.act_dim = act_dim
        self.min_std = float(min_std)          # piso de exploração (evita colapso do std)
        if init_log_std is None:
            init_log_std = tuple([math.log(0.6)] * act_dim)

        resolved_bc = None
        if bc_path:
            p = Path(bc_path)
            if not p.is_absolute() and not p.exists():
                candidate = MODEL_DIR / p
                resolved_bc = str(candidate if candidate.exists() else p)
            else:
                resolved_bc = str(p)

        self.actor = self._build_actor(obs_spaces, act_dim, resolved_bc)
        self.critic = self._build_critic(obs_spaces)

        # log_std como variável do AGENTE e incluída explicitamente nas variáveis
        # otimizadas. (Antes era `model._log_std = tf.Variable(...)`: no Keras 3 isso
        # NÃO entra em actor.trainable_variables -> o desvio ficava congelado em 0.61.)
        ls = list(init_log_std)[:act_dim] + [-0.7] * max(0, act_dim - len(init_log_std))
        self.log_std = tf.Variable(np.array(ls, dtype=np.float32), trainable=True, name='log_std')
        # --- init-actor: warm start de checkpoint RL anterior ---
        if init_actor_path:
            p = Path(init_actor_path)
            if not p.is_absolute() and not p.exists():
                p = MODEL_DIR / p
            src = tf.keras.models.load_model(str(p), compile=False)
            try:
                self.actor.set_weights(src.get_weights())
            except ValueError as e:
                raise RuntimeError(
                    f"[ERRO] Checkpoint {p} incompatível com o obs do env atual "
                    f"(o espaço de observação mudou? Treine do zero ou use --bc).") from e
            print(f"[INFO] actor inicializado de: {p}")
            std_path = Path(str(p).replace('multi_context_rl_actor', 'multi_context_rl_log_std')
                                .replace('.keras', '.npy'))
            if std_path.exists():
                self.log_std.assign(np.load(str(std_path)).astype(np.float32))
                print(f"[INFO] log_std restaurado de: {std_path}")
        if init_std is not None:
            self.log_std.assign(np.log(init_std) * np.ones_like(self.log_std.numpy()))
            print(f"[INFO] log_std inicializado em {init_std}")
        if init_critic_path:
            p = Path(init_critic_path)
            if not p.is_absolute() and not p.exists():
                p = MODEL_DIR / p
            src = tf.keras.models.load_model(str(p), compile=False)
            self.critic.set_weights(src.get_weights())
            print(f"[INFO] critic inicializado de: {p}")
        self.actor_opt = Adam(lr)
        self.critic_opt = Adam(critic_lr)

    # ------------------------------------------------------------------ modelos
    def _inputs(self, obs_spaces):
        return (Input(shape=obs_spaces['telemetry'].shape, name='telemetry'),
                Input(shape=obs_spaces['ctx_numeric'].shape, name='ctx_numeric'),
                Input(shape=(1,), dtype='int32', name='track_id'),
                Input(shape=(1,), dtype='int32', name='compound_id'))

    def _build_actor(self, obs_spaces, act_dim, bc_path):
        inp_tel, inp_ctx, inp_trk, inp_cmp = self._inputs(obs_spaces)
        emb_trk = Flatten()(Embedding(input_dim=20, output_dim=8)(inp_trk))
        emb_cmp = Flatten()(Embedding(input_dim=5, output_dim=4)(inp_cmp))

        # MLP simples, sem BatchNorm/Dropout (não se usa em PPO; além disso, nas versões
        # anteriores essas camadas não estavam ligadas ao grafo — faltava `x = ...`).
        x = Concatenate()([inp_tel, inp_ctx, emb_trk, emb_cmp])
        for units in (256, 128, 64, 32):
            x = Dense(units, activation='relu')(x)
        # Média LINEAR (sem tanh): com a política tanh-squashed (ver _act), uma
        # média ilimitada pode saturar o tanh quando necessário — com tanh na
        # média, a política nunca chegaria perto de ±1.
        mean = Dense(act_dim, activation=None, name='mean',
                     kernel_initializer=tf.keras.initializers.RandomNormal(stddev=0.01))(x)
        model = Model(inputs=[inp_tel, inp_ctx, inp_trk, inp_cmp], outputs=mean)

        # Viés inicial: longitudinal levemente positivo (anda para frente),
        # esterço neutro. Com squash, bias 0.3 -> tanh(0.3) ≈ 0.29 de throttle.
        bias = np.zeros(act_dim, dtype=np.float32)
        if act_dim == 2:
            bias[1] = 0.3                                                       # [steer, long]
        else:                                                                   # legado 3 dims
            bias[:min(2, act_dim)] = [0.5, -0.5][:min(2, act_dim)]
        model.get_layer('mean').bias.assign(bias)

        if bc_path:
            try:
                bc = tf.keras.models.load_model(bc_path, compile=False)
                src = [l for l in bc.layers if isinstance(l, Dense)]
                dst = [l for l in model.layers if isinstance(l, Dense) and l.name != 'mean']
                copied = 0
                for s, d in zip(src, dst):
                    sw, dw = s.get_weights(), d.get_weights()
                    if len(sw) == len(dw) and all(a.shape == b.shape for a, b in zip(sw, dw)):
                        d.set_weights(sw); copied += 1
                print(f"[INFO] BC: {copied} camadas Dense copiadas (as demais tinham shape incompatível).")
            except Exception as e:
                print(f"[WARN] Não carregou BC: {e}")
        return model

    def _build_critic(self, obs_spaces):
        inp_tel, inp_ctx, inp_trk, inp_cmp = self._inputs(obs_spaces)
        emb_trk = Flatten()(Embedding(input_dim=20, output_dim=8)(inp_trk))
        emb_cmp = Flatten()(Embedding(input_dim=5, output_dim=4)(inp_cmp))
        x = Concatenate()([inp_tel, inp_ctx, emb_trk, emb_cmp])
        for units in (256, 128, 64, 32):
            x = Dense(units, activation='relu')(x)
        out = Dense(1)(x)
        return Model(inputs=[inp_tel, inp_ctx, inp_trk, inp_cmp], outputs=out)

    # ------------------------------------------------------------ gaussiana (sem tfp)
    @staticmethod
    def _logp(mean, log_std, a):
        return tf.reduce_sum(-0.5 * tf.square((a - mean) / tf.exp(log_std)) - log_std - 0.5 * LOG2PI, axis=-1)

    @staticmethod
    def _entropy(log_std):
        return tf.reduce_sum(log_std + 0.5 * (1.0 + LOG2PI))

    # ------------------------------------------------------------ tanh-squash
    # Política Gaussiana squashed: a = tanh(z), z ~ N(mean, std). A ação ENVIADA
    # ao env já está limitada a (-1, 1) e é EXATAMENTE a cuja log-probabilidade é
    # pontuada no update — antes a amostra era crua, o env clipava, e o PPO
    # otimizava a probabilidade de ações que nunca foram executadas.
    _SQUASH_EPS = 1e-6

    @staticmethod
    def _squash(z):
        return tf.tanh(z)

    @classmethod
    def _squash_logp(cls, mean, log_std, z, a):
        """log p(a) = log N(z; mean, std) - Σ log(1 - tanh(z)²) (Jacobiano)."""
        logp = cls._logp(mean, log_std, z)
        det = tf.reduce_sum(tf.math.log(1.0 - tf.square(a) + cls._SQUASH_EPS), axis=-1)
        return logp - det

    @staticmethod
    def _atanh(a):
        a = tf.clip_by_value(a, -1.0 + 1e-6, 1.0 - 1e-6)
        return 0.5 * (tf.math.log1p(a) - tf.math.log1p(-a))

    # ------------------------------------------------------------------ atuação
    @tf.function(reduce_retracing=True)
    def _act(self, obs):
        mean = self.actor(obs, training=False)
        z = mean + tf.exp(self.log_std) * tf.random.normal(tf.shape(mean))
        a = self._squash(z)
        return a, self._squash_logp(mean, self.log_std, z, a)

    @tf.function(reduce_retracing=True)
    def _act_det(self, obs):
        """Ação determinística (avaliação): tanh(média), sem ruído."""
        return self._squash(self.actor(obs, training=False))

    def act_det_batch(self, obs):
        return self._act_det(_tf_obs(obs)).numpy()

    @tf.function(reduce_retracing=True)
    def _value(self, obs):
        return self.critic(obs, training=False)[:, 0]

    def act_batch(self, obs):
        a, logp = self._act(_tf_obs(obs))
        return a.numpy(), logp.numpy()

    def value_batch(self, obs):
        return self._value(_tf_obs(obs)).numpy()

    def act(self, obs):
        a, logp = self.act_batch({k: np.asarray(v)[None] for k, v in obs.items()})
        return a[0], logp[0]

    def value(self, obs):
        return self.value_batch({k: np.asarray(v)[None] for k, v in obs.items()})[0]

    # ------------------------------------------------------------------ update
    @tf.function(reduce_retracing=True)
    def _train_step(self, obs, act, old_logp, ret, adv):
        with tf.GradientTape() as tape:
            mean = self.actor(obs, training=False)
            # `act` é a ação SQUASHED executada no env. Recupera z = atanh(act) e
            # aplica a mesma correção de Jacobiano usada na amostragem — assim o
            # logp do update é consistente com o do rollout.
            z = self._atanh(act)
            logp = self._squash_logp(mean, self.log_std, z, act)
            ratio = tf.exp(logp - old_logp)
            surr1 = ratio * adv
            surr2 = tf.clip_by_value(ratio, 1.0 - self.clip, 1.0 + self.clip) * adv
            policy_loss = -tf.reduce_mean(tf.minimum(surr1, surr2))
            ent = self._entropy(self.log_std)
            v = self.critic(obs, training=False)[..., 0]
            v_loss = tf.reduce_mean(tf.square(v - ret))
            total = (policy_loss - self.ent_coef * ent) + self.vf_coef * v_loss

        a_vars = list(self.actor.trainable_variables) + [self.log_std]
        c_vars = list(self.critic.trainable_variables)
        grads = tape.gradient(total, a_vars + c_vars)
        ga, gc = grads[:len(a_vars)], grads[len(a_vars):]
        ga, _ = tf.clip_by_global_norm(ga, self.max_grad)
        gc, _ = tf.clip_by_global_norm(gc, self.max_grad)
        self.actor_opt.apply_gradients(zip(ga, a_vars))
        self.critic_opt.apply_gradients(zip(gc, c_vars))
        self.log_std.assign(tf.clip_by_value(self.log_std,
                                             math.log(self.min_std), math.log(1.0)))
        approx_kl = tf.reduce_mean(old_logp - logp)
        return policy_loss, v_loss, ent, approx_kl

    # ------------------------------------------------------------------ salvar
    def _save(self, out_dir, suffix="", meta=None):
        self.actor.save(str(out_dir / f'multi_context_rl_actor{suffix}.keras'))
        self.critic.save(str(out_dir / f'multi_context_rl_critic{suffix}.keras'))
        np.save(str(out_dir / f'multi_context_rl_log_std{suffix}.npy'), self.log_std.numpy())
        # Rastreabilidade (Fase F): qual iteração/métricas geraram ESTE artefato.
        # O checkpoint "best" não é mais uma caixa-preta: o JSON registra
        # iteração, lap%, retorno e std no momento do salvamento.
        if meta is not None:
            import json
            meta_path = out_dir / f'training_meta{suffix or "_last"}.json'
            try:
                existing = {}
                if meta_path.exists():
                    import json as _j
                    existing = _j.load(open(meta_path))
            except Exception:
                existing = {}
            existing.update(meta)
            with open(meta_path, 'w') as f:
                json.dump(existing, f, indent=2, default=float)

    # ------------------------------------------------------------------ treino
    def train(self, env, n_iters=500, steps_per_roll=2048, epochs=10, batch_size=256, save_dir=None):
        """Ambiente único: embrulha em um SyncVectorEnv(1) e reaproveita o loop vetorizado."""
        vec_env = gym.vector.SyncVectorEnv([lambda: env])
        self.train_vectorized(vec_env, n_envs=1, n_iters=n_iters, steps_per_roll=steps_per_roll,
                              epochs=epochs, batch_size=batch_size, save_dir=save_dir)

    def train_vectorized(self, vec_env, n_envs, n_iters=500, steps_per_roll=256, epochs=10,
                         batch_size=256, save_dir=None, verbose_episodes=False):
        out_dir = Path(save_dir or MODEL_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        next_step = _autoreset_is_next_step(vec_env)
        print(f"[INFO] gymnasium {gym.__version__} | autoreset NEXT_STEP (mascarando transição-lixo): {next_step}")

        obs, _ = vec_env.reset()
        ep_ret = np.zeros(n_envs)
        ep_len = np.zeros(n_envs, dtype=int)
        prev_done = np.zeros(n_envs, dtype=bool)
        recent = deque(maxlen=200)           # retornos dos últimos episódios (p/ "best")
        recent_laps = deque(maxlen=200)      # 1.0 = volta completada
        recent_lap_times = deque(maxlen=50) # tempos das voltas VÁLIDAS (s) p/ pace
        best_score = -np.inf

        for it in range(n_iters):
            buffers = {k: [] for k in obs.keys()}
            act_buf, logp_buf, rew_buf, val_buf, done_buf, term_buf, valid_buf = \
                [], [], [], [], [], [], []
            it_rets, it_lens, it_prog = [], [], []
            parts_sum = {}
            n_parts_eps = 0

            for _ in range(steps_per_roll):
                a, logp = self.act_batch(obs)
                v = self.value_batch(obs)
                next_obs, r, term, trunc, infos = vec_env.step(a)
                done = np.logical_or(term, trunc)
                valid = ~prev_done if next_step else np.ones(n_envs, dtype=bool)

                for k in buffers:
                    buffers[k].append(obs[k])
                act_buf.append(a); logp_buf.append(logp); rew_buf.append(r)
                val_buf.append(v); done_buf.append(done); term_buf.append(term)
                valid_buf.append(valid)

                ep_ret += r * valid
                ep_len += valid.astype(int)
                for i in np.where(done & valid)[0]:
                    it_rets.append(ep_ret[i]); it_lens.append(ep_len[i]); recent.append(ep_ret[i])
                    lap_done = False
                    if isinstance(infos, dict):
                        pm = infos.get('progress_m')
                        if pm is not None:
                            it_prog.append(float(np.asarray(pm).reshape(-1)[i] if np.ndim(pm) else pm))
                        cl = infos.get('completed_lap')
                        if cl is not None:
                            lap_done = bool(np.asarray(cl).reshape(-1)[i] if np.ndim(cl) else cl)
                        rp = infos.get('reward_parts')
                        if isinstance(rp, dict):
                            for k0, arr0 in rp.items():
                                if k0.startswith('_'):   # máscaras internas do vector env
                                    continue
                                val0 = np.asarray(arr0, dtype=np.float64).reshape(-1)
                                parts_sum[k0] = parts_sum.get(k0, 0.0) + float(val0[min(i, len(val0)-1)])
                    recent_laps.append(1.0 if lap_done else 0.0)
                    if lap_done:
                        lt = None
                        try:
                            st = env.states[drv.driver_id]
                            lt = st.last_lap_time_s
                        except Exception:
                            pass
                        if lt:
                            recent_lap_times.append(float(lt))
                    n_parts_eps += 1
                    if verbose_episodes:
                        print(f"[iter {it + 1}] env={i} ep_return={ep_ret[i]:.2f} len={ep_len[i]}"
                              f"{' LAP' if lap_done else ''}")
                    ep_ret[i] = 0.0; ep_len[i] = 0
                prev_done = done
                obs = next_obs

            # --- GAE por ambiente: BOOTSTRAP em truncamento ---
            # `term` corta a cadeia (V(s')=0); `trunc` NÃO corta — o episódio
            # acabou pelo limite de steps, não por falha (antes trunc virava
            # terminal no GAE: subvalorizava estados de fim de janela).
            rew_arr = np.array(rew_buf, dtype=np.float32)      # (T, n_envs)
            val_arr = np.array(val_buf, dtype=np.float32)
            done_arr = np.array(done_buf, dtype=np.float32)    # term|trunc: fim de episódio p/ stats
            term_arr = np.array(term_buf, dtype=np.float32)    # só terminal REAL p/ o GAE
            valid_arr = np.array(valid_buf, dtype=bool)
            last_val = self.value_batch(obs)

            adv = np.zeros_like(rew_arr)
            gae = np.zeros(n_envs, dtype=np.float32)
            for t in reversed(range(len(rew_arr))):
                next_v = val_arr[t + 1] if t + 1 < len(val_arr) else last_val
                delta = rew_arr[t] + self.gamma * next_v * (1 - term_arr[t]) - val_arr[t]
                gae = delta + self.gamma * self.lam * (1 - term_arr[t]) * gae
                adv[t] = gae
            ret = adv + val_arr

            # --- achata (T, n_envs, ...) e descarta as transições-lixo do autoreset ---
            mask = valid_arr.reshape(-1)
            obs_tensors = {k: np.array(v, dtype=np.int32 if k in INT_KEYS else np.float32)
                           .reshape(-1, *np.array(v).shape[2:])[mask]
                           for k, v in buffers.items()}
            act_arr = np.array(act_buf, dtype=np.float32).reshape(-1, self.act_dim)[mask]
            logp_arr = np.array(logp_buf, dtype=np.float32).reshape(-1)[mask]
            ret_flat = ret.reshape(-1)[mask]
            adv_flat = adv.reshape(-1)[mask]
            adv_flat = (adv_flat - adv_flat.mean()) / (adv_flat.std() + 1e-8)

            # --- PPO update (com early-stop por KL) ---
            n = len(act_arr)
            idx = np.arange(n)
            kls, ents, vls = [], [], []
            stop = False
            for _ in range(epochs):
                np.random.shuffle(idx)
                for s in range(0, n, batch_size):
                    b = idx[s:s + batch_size]
                    if len(b) < 32:
                        continue
                    batch_obs = _tf_obs({k: v[b] for k, v in obs_tensors.items()})
                    _, vl, ent, kl = self._train_step(batch_obs, act_arr[b], logp_arr[b], ret_flat[b], adv_flat[b])
                    kls.append(float(kl)); ents.append(float(ent)); vls.append(float(vl))
                    if float(kl) > 1.5 * self.target_kl:
                        stop = True
                        break
                if stop:
                    break

            # --- log por iteração (métricas de pilotagem, não só retorno) ---
            mean_ret = float(np.mean(it_rets)) if it_rets else float('nan')
            mean_len = float(np.mean(it_lens)) if it_lens else float('nan')
            prog = f" prog={np.mean(it_prog):6.1f}m" if it_prog else ""
            std = np.exp(self.log_std.numpy())
            parts_str = ""
            if parts_sum and n_parts_eps:
                parts_str = " | parts={" + ", ".join(
                    f"{k}:{v / n_parts_eps:+.2f}" for k, v in sorted(parts_sum.items())) + "}"
            print(f"[iter {it + 1}/{n_iters}] eps={len(it_rets):3d} ret={mean_ret:8.2f} len={mean_len:7.1f}{prog}"
                  f" | std={np.round(std, 2)} kl={np.mean(kls) if kls else 0:.4f}"
                  f" vloss={np.mean(vls) if vls else 0:.1f}"
                  f" lap%={(100 * np.mean(recent_laps)) if recent_laps else 0.0:5.1f}{parts_str}"
                  + (f" lap_med={np.median(recent_lap_times):6.1f}s" if recent_lap_times else ""),
                  flush=True)

            # --- checkpoints: periódico + MELHOR ---
            # Critério principal: TAXA DE CONCLUSÃO DE VOLTA (não retorno, que pode
            # subir com exploits de respawn). Desempate por retorno médio.
            meta = {"iteration": it + 1,
                    "lap_pct": float(100 * np.mean(recent_laps)) if recent_laps else 0.0,
                    "mean_return": float(np.mean(recent)) if recent else None,
                    "std": std.tolist(),
                    "kl": float(np.mean(kls)) if kls else None,
                    "median_lap_time_s": (float(np.median(recent_lap_times))
                                          if recent_lap_times else None)}
            if (it + 1) % 10 == 0:
                self._save(out_dir, meta=meta)
                print(f"[iter {it + 1}] checkpoint salvo em {out_dir}")
            if len(recent) >= 50:
                score = 1000.0 * float(np.mean(recent_laps)) + float(np.mean(recent)) / 100.0
                if score > best_score:
                    best_score = score
                    self._save(out_dir, suffix="_best", meta=meta)
                    print(f"[iter {it + 1}] novo MELHOR (lap%={100 * np.mean(recent_laps):.1f} "
                          f"ret={np.mean(recent):.2f}) -> *_best.keras")

        self._save(out_dir, meta={**meta, "iteration": n_iters, "final": True})
        print(f"[CONCLUÍDO] Modelo final salvo em {out_dir}")


def make_env_fn(track="interlagos", reference_csv=None, driver_id='HAM', track_id=0, compound_id=0,
                random_start_prob=0.3, f1_year=2024, f1_session="R", fastf1_cache_dir=None,
                grip_random=None, start_zones=None, zone_frac=0.5, obs_mode='legacy',
                sf_reward=0.80, allow_respawn=True):
    def _init(sf_reward=0.80):
        return F1MultiContextEnv(
            track=track,
            reference_csv=reference_csv,
            driver_id=driver_id,
            track_id=track_id,
            compound_id=compound_id,
            random_start_prob=random_start_prob,
            f1_year=f1_year,
            f1_session=f1_session,
            fastf1_cache_dir=fastf1_cache_dir,
            grip_random=grip_random,
            start_zones=start_zones,
            zone_frac=zone_frac,
            obs_mode=obs_mode,
            sf_reward=sf_reward,
            allow_respawn=allow_respawn,
        )
    return _init


def main():
    import argparse
    from gymnasium.vector import AsyncVectorEnv

    parser = argparse.ArgumentParser(description="Treinamento PPO Multi-Contexto F1")
    parser.add_argument("--n-envs", type=int, default=8)
    parser.add_argument("--iters", type=int, default=500)
    parser.add_argument("--steps-per-roll", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--driver-id", type=str, default="HAM")
    parser.add_argument("--track-id", type=int, default=0)
    parser.add_argument("--compound-id", type=int, default=0)
    parser.add_argument("--bc-path", type=str, default=str(DEFAULT_BC_PATH))
    parser.add_argument("--bc", action="store_true", help="Inicializar com pesos do BC (default: do zero)")
    parser.add_argument("--track", type=str, default="interlagos",
                        help="Nome do evento FastF1 (ex.: 'Monaco', 'Silverstone') ou 'interlagos' "
                             "(= GP de São Paulo). Dados reais baixados e cacheados; fallback: São Paulo.")
    parser.add_argument("--year", type=int, default=2024, help="Ano da sessão FastF1")
    parser.add_argument("--session", type=str, default="R", help="Sessão FastF1 (R, Q, S, FP1...)")
    parser.add_argument("--reference-csv", type=str, default=None)
    parser.add_argument("--save-dir", type=str, default=str(MODEL_DIR))
    parser.add_argument("--random-start-prob", type=float, default=0.5,
                        help="Fração dos episódios que começam em ponto aleatório da pista, já com velocidade")
    parser.add_argument("--single-env", action="store_true")
    parser.add_argument("--init-actor", type=str, default=None,
                        help="Checkpoint .keras do actor p/ continuar treino (ex.: multi_context_rl_actor_best.keras)")
    parser.add_argument("--init-critic", type=str, default=None)
    parser.add_argument("--init-std", type=float, default=None,
                        help="log_std inicial p/ continuacao (mais exploracao); "
                             "ex.: 0.5 — quebra o atrator tanh(+0.99) nas retas")
    parser.add_argument("--grip-random", type=float, nargs=2, default=None, metavar=("LO", "HI"),
                        help="domain randomization de aderência: grip_override ~ U[lo, hi] por episódio. "
                             "Ex.: --grip-random 0.75 1.0 (realista é ~0.79 em pista quente).")
    parser.add_argument("--start-zones", type=str, default=None,
                        help="currículo de aproximação (Fase D): zonas 's_lo:s_hi,...' antes de curvas "
                             "críticas. Ex.: '1748:1948,2009:2209,3860:4060'")
    parser.add_argument("--zone-frac", type=float, default=0.5,
                        help="fração dos starts aleatórios que usam as zonas")
    parser.add_argument("--tracks", type=str, default=None,
                        help="Fase 4: pool multi-pista 'A,B,C' — distribuídas "
                             "round-robin entre os workers (generalização v7). "
                             "Use 'auto' nas --start-zones para zonas por geometria.")
    parser.add_argument("--allow-respawn", type=lambda x: x.lower() in ('true','1','yes'),
                        default=True,
                        help="CRÍTICO: False = episódio TERMINA no crash (autonomia real). "
                             "True (default histórico) = respawn fabrica voltas no lap%.")
    parser.add_argument("--sf-reward", type=float, default=0.80,
                        help="fator de segurança do v_allow da recompensa (0.80=legado, 1.00=física pura)")
    parser.add_argument("--obs-mode", type=str, default='legacy',
                        choices=['legacy', 'edge'],
                        help="esquema de observação: legacy=23d (v2-v7) | edge=34d (v8, +11 raios)")
    parser.add_argument("--track-id-embed", type=int, default=0,
                        help="id passado no obs track_id (0 = força a política a "
                             "usar só a geometria local — recomendado p/ generalizar)")
    args = parser.parse_args()
    grip_random = tuple(args.grip_random) if args.grip_random else None
    start_zones = None
    if args.start_zones and args.start_zones != 'auto':
        start_zones = [tuple(float(v) for v in z.split(':')) for z in args.start_zones.split(',')]
    elif args.start_zones == 'auto':
        start_zones = 'auto'   # o ENV detecta as zonas pela geometria de CADA pista

    ref_csv = None
    if args.reference_csv:
        ref_csv = Path(args.reference_csv)
        if not ref_csv.is_absolute() and not ref_csv.exists():
            if (MODEL_DIR / ref_csv).exists():
                ref_csv = MODEL_DIR / ref_csv
            elif (PROJECT_ROOT / ref_csv).exists():
                ref_csv = PROJECT_ROOT / ref_csv

    bc_path = Path(args.bc_path) if args.bc else None

    if args.single_env:
        env = F1MultiContextEnv(track=args.track, reference_csv=str(ref_csv) if ref_csv else None,
                                driver_id=args.driver_id, track_id=args.track_id,
                                compound_id=args.compound_id, random_start_prob=args.random_start_prob,
                                f1_year=args.year, f1_session=args.session,
                                obs_mode=args.obs_mode,
                                allow_respawn=args.allow_respawn)
        try:
            agent = MultiContextPPOAgent(obs_spaces=env.observation_space, act_dim=env.action_space.shape[0],
                                         bc_path=str(bc_path) if bc_path and bc_path.exists() else None, init_actor_path=args.init_actor,      # <<< NOVO
                                         init_critic_path=args.init_critic)
            agent.train(env=env, n_iters=args.iters, steps_per_roll=args.steps_per_roll * args.n_envs,
                        epochs=args.epochs, batch_size=args.batch_size, save_dir=args.save_dir)
        finally:
            env.close()
    else:
        pool = ([t.strip() for t in args.tracks.split(',')] if args.tracks else None)
        env_fns = []
        for w in range(args.n_envs):
            tk = (pool[w % len(pool)] if pool else args.track)
            env_fns.append(make_env_fn(
                track=tk, reference_csv=str(ref_csv) if ref_csv else None,
                driver_id=args.driver_id, track_id=args.track_id_embed,
                compound_id=args.compound_id, random_start_prob=args.random_start_prob,
                f1_year=args.year, f1_session=args.session, grip_random=grip_random,
                start_zones=start_zones, zone_frac=args.zone_frac,
                obs_mode=args.obs_mode, sf_reward=args.sf_reward,
                allow_respawn=args.allow_respawn))
        if pool:
            print(f"[INFO] pool multi-pista ({len(pool)}): {pool} | "
                  f"track_id={args.track_id_embed} (geometria-local)")
        vec_env = AsyncVectorEnv(env_fns, context="spawn")
        try:
            agent = MultiContextPPOAgent(obs_spaces=vec_env.single_observation_space,
                                         act_dim=vec_env.single_action_space.shape[0],
                                         bc_path=str(bc_path) if bc_path and bc_path.exists() else None, init_actor_path=args.init_actor,
                                         init_critic_path=args.init_critic, init_std=args.init_std)
            agent.train_vectorized(vec_env, n_envs=args.n_envs, n_iters=args.iters,
                                   steps_per_roll=args.steps_per_roll, epochs=args.epochs,
                                   batch_size=args.batch_size, save_dir=args.save_dir)
        finally:
            vec_env.close()


if __name__ == "__main__":
    main()