# archive/scripts — proveniência (FASE 0.1 v15, 2026-10-14)

Scripts históricos movidos de model_train/ (nenhum código vivo importa; verificado
por grep em tests/, model_train/, scripts/ antes da movimentação — o train.py era o
único importador de model_multi_context e veio junto). NUNCA deletados.
- train.py, train_multi_context.py, train_bc_v2/v5.py, rl_training.py,
  model_multi_context.py: pipelines supersededos pelo train_dagger.py.
- evaluate_policy.py: duplicata legada do eval_policy.py (canonical).
- fase_*.py, sanity_check.py, benchmark_policies.py, sector_benchmark.py,
  measure_limits.py, physics_radius_calibration.py: one-offs de investigação
  das Metas A/B (histórico na AUDITORIA_RL.md).
FICA em model_train/: train_multi_context_ppo.py (MultiContextPPOAgent —
importado pelo train_dagger.py e tests), teacher_benchmark.py, eval_policy.py,
eval_protocol.py, eval_traffic_compare.py, eval_teacher_solo.py,
gate_checkpoint.py, diag_suzuka.py, slot_swap_analysis.py, race_diagnostic.py.
