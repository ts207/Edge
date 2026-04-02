# Promotion seed inventory

- candidate_count: `13`
- status_counts: `{"needs_repair": 1, "test_now": 12}`
- source_mode: `governance-aware fallback queue from Wave 3 contracts and episode registry`

## Candidate queue
### THESIS_VOL_SHOCK
- source_type: `event`
- source_contract_ids: `VOL_SHOCK`
- governance: tier `A`, role `trigger`, disposition `primary_trigger_candidate`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect volatility expansion and directional follow-through after onset.

### THESIS_LIQUIDITY_VACUUM
- source_type: `event`
- source_contract_ids: `LIQUIDITY_VACUUM`
- governance: tier `A`, role `trigger`, disposition `primary_trigger_candidate`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect unstable liquidity conditions that either amplify the move or attract a repair response.

### THESIS_LIQUIDITY_STRESS_DIRECT
- source_type: `event`
- source_contract_ids: `LIQUIDITY_STRESS_DIRECT`
- governance: tier `B`, role `trigger`, disposition `secondary_or_confirm`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect volatility expansion and directional follow-through after onset.

### THESIS_BASIS_DISLOC
- source_type: `event`
- source_contract_ids: `BASIS_DISLOC`
- governance: tier `A`, role `trigger`, disposition `primary_trigger_candidate`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect volatility expansion and directional follow-through after onset.

### THESIS_FND_DISLOC
- source_type: `event`
- source_contract_ids: `FND_DISLOC`
- governance: tier `A`, role `trigger`, disposition `primary_trigger_candidate`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect volatility expansion and directional follow-through after onset.

### THESIS_LIQUIDATION_CASCADE
- source_type: `event`
- source_contract_ids: `LIQUIDATION_CASCADE`
- governance: tier `A`, role `trigger`, disposition `primary_trigger_candidate`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect forced flow to culminate in either continued stress or a sharp repair window.

### THESIS_VOL_SHOCK_LIQUIDITY_CONFIRM
- source_type: `event_plus_confirm`
- source_contract_ids: `VOL_SHOCK|LIQUIDITY_VACUUM`
- governance: tier `A`, role `confirm`, disposition `seed_review_required`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect volatility expansion and directional follow-through after onset.

### THESIS_LIQUIDITY_VACUUM_CASCADE_CONFIRM
- source_type: `event_plus_confirm`
- source_contract_ids: `LIQUIDITY_VACUUM|LIQUIDATION_CASCADE`
- governance: tier `A`, role `confirm`, disposition `seed_review_required`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect forced flow to culminate in either continued stress or a sharp repair window.

### THESIS_BASIS_FND_CONFIRM
- source_type: `event_plus_confirm`
- source_contract_ids: `BASIS_DISLOC|FND_DISLOC`
- governance: tier `A`, role `confirm`, disposition `seed_review_required`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect unstable liquidity conditions that either amplify the move or attract a repair response.

### THESIS_LIQUIDATION_DEPTH_CONFIRM
- source_type: `event_plus_confirm`
- source_contract_ids: `LIQUIDATION_CASCADE|LIQUIDITY_STRESS_DIRECT`
- governance: tier `A/B`, role `confirm`, disposition `seed_review_required`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect forced flow to culminate in either continued stress or a sharp repair window.

### THESIS_EP_VOLATILITY_BREAKOUT
- source_type: `episode`
- source_contract_ids: `EP_VOLATILITY_BREAKOUT`
- governance: tier `B`, role `trigger`, disposition `secondary_trigger_candidate`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect volatility expansion and directional follow-through after onset.

### THESIS_EP_LIQUIDITY_SHOCK
- source_type: `episode`
- source_contract_ids: `EP_LIQUIDITY_SHOCK`
- governance: tier `B`, role `trigger`, disposition `secondary_trigger_candidate`
- promotion_status: `test_now`
- next_action: `run_seed_tests`
- horizon_guess: `8-24 bars`
- expected_direction_or_path: Expect volatility expansion and directional follow-through after onset.

### THESIS_EP_DISLOCATION_REPAIR
- source_type: `episode`
- source_contract_ids: `EP_DISLOCATION_REPAIR`
- governance: tier `C`, role `context`, disposition `context_only`
- promotion_status: `needs_repair`
- next_action: `repair_governance_or_role_conflict`
- horizon_guess: `8-32 bars`
- expected_direction_or_path: Expect bounded repair or convergence after the dislocation resolves.
