| config | id | family | authority | policy | backend | models | real | priv | capability runs | other envs |
|---|---|---|---|---|---|---|---|---|---|---|
| c0_oracle | c0 | classical_baseline | waypoint | oracle_waypoint | free |  | - | Y | 33 | grid_nav:1, grid_nav_aerovla:3, grid_nav_onfly_native_long:5 |
| c10_periodic_hierarchy | c10 | hybrid_stack | direct_vla | mock_vla | simulated | sim-vla-reasoner | - | - | 0 |  |
| c11_chunked_hierarchy | c11 | hybrid_stack | direct_vla | chunk_vla | simulated | sim-vla-reasoner | - | - | 0 |  |
| c12_async_hierarchy | c12 | hybrid_stack | direct_vla | chunk_vla | simulated | sim-vla-reasoner | - | - | 0 |  |
| c13_triggered_hierarchy | c13 | hybrid_stack | direct_vla | chunk_vla | simulated | sim-vla-reasoner | - | - | 0 |  |
| c14_world_model | c14 | hybrid_stack | direct_vla | world_model_vla | simulated | sim-vla-reasoner | - | - | 0 |  |
| c1_aerialclaw_qwen4_shared | c1_aerialclaw_qwen4_shared | llm_tool_planner | skill | aerialclaw_agent | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_aerovla:3 |
| c1_capability_gemma_dev | c1_capability_gemma_dev | llm_tool_planner | skill | aerialclaw_agent | ollama | gemma4:e2b | Y | - | 30 |  |
| c1_inspected_search_gemma_dev | c1_inspected_search_gemma_dev | llm_tool_planner | skill | aerialclaw_visual_agent | ollama | gemma4:e2b | Y | - | 2 |  |
| c1_llm_skills | c1 | llm_tool_planner | skill | aerialclaw_agent | ollama | gpt-oss:20b | Y | - | 0 | grid_nav:21, grid_nav_aerovla:1, object_search:10 |
| c1_ordered_requested_gemma_dev | c1_ordered_requested_gemma_dev | llm_tool_planner | skill | aerialclaw_ordered_visual | ollama | gemma4:e2b | Y | - | 2 |  |
| c1_ordered_visual_gemma_dev | c1_ordered_visual_gemma_dev | llm_tool_planner | skill | aerialclaw_ordered_visual | ollama | gemma4:e2b | Y | - | 2 |  |
| c1_visual_search_gemma_dev | c1_visual_search_gemma_dev | llm_tool_planner | skill | aerialclaw_visual_agent | ollama | gemma4:e2b | Y | - | 6 |  |
| c1_visual_tools_gemma_dev | c1_visual_tools_gemma_dev | llm_tool_planner | skill | aerialclaw_visual_agent | ollama | gemma4:e2b | Y | - | 2 |  |
| c1_visual_tools_refined_gemma_dev | c1_visual_tools_refined_gemma_dev | llm_tool_planner | skill | aerialclaw_visual_agent | ollama | gemma4:e2b | Y | - | 4 |  |
| c2_spf | c2_spf | vlm_semantic_waypointer | waypoint | spf_waypoint | ollama | qwen3-vl:8b | Y | - | 0 | grid_nav_aerovla:1, grid_nav_vision:5 |
| c2_spf_qwen4_current_dev | c2_spf_qwen4_current_dev | vlm_semantic_waypointer | waypoint | spf_waypoint | ollama | qwen3-vl:4b | Y | - | 2 |  |
| c2_spf_qwen4_shared | c2_spf_qwen4_shared | vlm_semantic_waypointer | waypoint | spf_waypoint | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_aerovla:2 |
| c2_spf_rgbd_arrival_qwen4_dev | c2_spf_rgbd_arrival_qwen4_dev | vlm_semantic_waypointer | waypoint | spf_rgbd_arrival | ollama | qwen3-vl:4b | Y | - | 2 |  |
| c2_vlm_waypoint | c2 | vlm_semantic_waypointer | waypoint | vlm_waypoint | simulated | sim-vlm | - | - | 0 | grid_nav:1, grid_nav_vision:4 |
| c2g_gemma_waypoint | c2g | vlm_semantic_waypointer | waypoint | vlm_point_waypoint | ollama | gemma3:4b | Y | - | 0 | grid_nav_vision:15 |
| c3_onfly_gemma | c3_onfly_gemma | hybrid_stack | waypoint | onfly_decision | ollama | gemma3:4b | Y | - | 0 |  |
| c3_onfly_qwen | c3_onfly_qwen | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:8b | Y | - | 0 | grid_nav_onfly:3 |
| c3_onfly_qwen4 | c3_onfly_qwen4 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_aerovla:1, grid_nav_onfly:3 |
| c3_onfly_qwen4_native_dynamics | c3_onfly_qwen4_native_dynamics | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c3_onfly_qwen4_native_shield | c3_onfly_qwen4_native_shield | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 |  |
| c3_onfly_qwen4_shared | c3_onfly_qwen4_shared | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_aerovla:2 |
| c3_spf_qwen4_current_dev | c3_spf_qwen4_current_dev | hybrid_stack | waypoint | spf_waypoint | ollama | qwen3-vl:4b | Y | - | 2 |  |
| c3_spf_rgbd_arrival_qwen4_dev | c3_spf_rgbd_arrival_qwen4_dev | hybrid_stack | waypoint | spf_rgbd_arrival | ollama | qwen3-vl:4b | Y | - | 0 |  |
| c3_verifier | c3 | hybrid_stack | waypoint | vlm_waypoint | simulated | sim-vlm | - | - | 0 | grid_nav:1 |
| c3g_gemma_verifier | c3g | hybrid_stack | waypoint | vlm_point_waypoint | ollama | gemma3:4b | Y | - | 0 | grid_nav_vision:4 |
| c4_onfly_gemma | c4_onfly_gemma | hybrid_stack | waypoint | onfly_decision | ollama | gemma3:4b | Y | - | 0 |  |
| c4_onfly_qwen | c4_onfly_qwen | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:8b | Y | - | 0 |  |
| c4_periodic_monitor | c4 | hybrid_stack | waypoint | vlm_waypoint | simulated | sim-vlm-dual | - | - | 0 |  |
| c4g_gemma_monitor | c4g | hybrid_stack | waypoint | vlm_point_waypoint | ollama | gemma3:4b | Y | - | 0 |  |
| c5_arrival_memory_gemma_dev | c5_arrival_memory_gemma_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 2 |  |
| c5_arrival_window_gemma_dev | c5_arrival_window_gemma_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 4 |  |
| c5_capability_gemma_dev | c5_capability_gemma_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 32 |  |
| c5_clutter_attributes_gemma_dev | c5_clutter_attributes_gemma_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_depth_v2_dev:2 |
| c5_clutter_qwen4_validated_dev | c5_clutter_qwen4_validated_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_depth_v2_dev:2 |
| c5_clutter_stable_gemma_dev | c5_clutter_stable_gemma_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_depth_v2_dev:2 |
| c5_free_vlm_router_dev | c5_free_vlm_router_dev | hybrid_stack | waypoint | onfly_decision | free_vlm_router | free-vlm-router | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c5_gemini_flash_target_stop_dev | c5_gemini_flash_target_stop_dev | hybrid_stack | waypoint | onfly_decision | gemini | gemini-3.5-flash | Y | - | 0 | grid_nav_onfly_native_dynamics:3 |
| c5_gemma4_e2b_baseline_dev | c5_gemma4_e2b_baseline_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_native_dynamics:5 |
| c5_gemma4_e2b_fresh_view_dev | c5_gemma4_e2b_fresh_view_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_native_dynamics:5 |
| c5_gemma4_e2b_projector_dev | c5_gemma4_e2b_projector_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b-visionfix-dev | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c5_gemma4_e2b_runtime_fixed_dev | c5_gemma4_e2b_runtime_fixed_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 |  |
| c5_gemma4_e2b_runtime_fixed_target_stop_dev | c5_gemma4_e2b_runtime_fixed_target_stop_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_native_dynamics:5 |
| c5_gemma4_e2b_target_stop_dev | c5_gemma4_e2b_target_stop_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 |  |
| c5_gemma_attribute_guard_dev | c5_gemma_attribute_guard_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c5_gemma_fresh_guarded_monitor_dev | c5_gemma_fresh_guarded_monitor_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c5_gemma_goal_yaw_dev | c5_gemma_goal_yaw_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c5_gemma_ground_monitor_dev | c5_gemma_ground_monitor_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c5_gemma_grounded_policy_dev | c5_gemma_grounded_policy_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c5_gemma_guarded_monitor_dev | c5_gemma_guarded_monitor_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_depth_v2_dev:6, grid_nav_onfly_native_dynamics:1 |
| c5_hover_context_gemma_dev | c5_hover_context_gemma_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 2 |  |
| c5_hover_gemma_dev | c5_hover_gemma_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 2 |  |
| c5_hover_level_gemma_dev | c5_hover_level_gemma_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 6 |  |
| c5_hover_stable_gemma_dev | c5_hover_stable_gemma_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 4 |  |
| c5_keyframe_memory | c5 | hybrid_stack | waypoint | vlm_waypoint | simulated | sim-vlm-dual | - | - | 0 |  |
| c5_observed_view_return_qwen4_dev | c5_observed_view_return_qwen4_dev | hybrid_stack | waypoint | vlm_observed_view_return | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_depth_v2_dev:2 |
| c5_onfly_active_dev | c5_onfly_active_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma4:e2b | Y | - | 0 |  |
| c5_onfly_fence_dev | c5_onfly_fence_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_native_dynamics:3 |
| c5_onfly_gemma | c5_onfly_gemma | hybrid_stack | waypoint | onfly_decision | ollama | gemma3:4b | Y | - | 0 | grid_nav_onfly:4 |
| c5_onfly_gemma4b_direction_dev | c5_onfly_gemma4b_direction_dev | hybrid_stack | waypoint | onfly_decision | ollama | gemma3:4b, qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_native_dynamics:2, grid_nav_onfly_native_long:5 |
| c5_onfly_qwen | c5_onfly_qwen | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:8b | Y | - | 0 | grid_nav_onfly:13 |
| c5_onfly_qwen4 | c5_onfly_qwen4 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly:1 |
| c5_onfly_qwen4_corridor_frontier_dev | c5_onfly_qwen4_corridor_frontier_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_native_dynamics:3 |
| c5_onfly_qwen4_coverage_dev | c5_onfly_qwen4_coverage_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_native_dynamics:4 |
| c5_onfly_qwen4_direction_dev | c5_onfly_qwen4_direction_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c5_onfly_qwen4_native_dynamics | c5_onfly_qwen4_native_dynamics | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_native_dynamics:30, grid_nav_onfly_native_long:5 |
| c5_onfly_qwen4_shared | c5_onfly_qwen4_shared | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_aerovla:2 |
| c5_onfly_qwen4_spf_step_dev | c5_onfly_qwen4_spf_step_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_native_dynamics:3 |
| c5_onfly_qwen_native_dynamics | c5_onfly_qwen_native_dynamics | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:8b | Y | - | 0 | grid_nav_onfly_native_dynamics:1 |
| c5_onfly_stop_fence_dev | c5_onfly_stop_fence_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 |  |
| c5_onfly_target_stop_dev | c5_onfly_target_stop_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_native_dynamics:6 |
| c5_recovery_fresh_qwen4_dev | c5_recovery_fresh_qwen4_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_onfly_depth_v2_dev:2 |
| c5_route_direction_s1060 | c5_route_direction_s1060 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_route_direction_s1061 | c5_route_direction_s1061 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_route_direction_s1062 | c5_route_direction_s1062 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_route_direction_s1063 | c5_route_direction_s1063 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_route_direction_s1064 | c5_route_direction_s1064 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_route_hint_s1060 | c5_route_hint_s1060 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_route_hint_s1061 | c5_route_hint_s1061 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_route_hint_s1062 | c5_route_hint_s1062 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_route_hint_s1063 | c5_route_hint_s1063 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_route_hint_s1064 | c5_route_hint_s1064 | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | Y | 0 | grid_nav_onfly_native_long:1 |
| c5_target_commitment_off_qwen4_dev | c5_target_commitment_off_qwen4_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_clutter_240_dev:6 |
| c5_target_commitment_qwen4_dev | c5_target_commitment_qwen4_dev | hybrid_stack | waypoint | onfly_decision | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_clutter_240_dev:6, grid_nav_onfly_depth_v2_dev:5 |
| c5g_gemma_keyframe | c5g | hybrid_stack | waypoint | vlm_point_waypoint | ollama | gemma3:4b | Y | - | 0 |  |
| c6_pmr_qwen4_gptoss | c6_pmr_qwen4_gptoss | selective_recovery | waypoint | onfly_decision | role_router | gpt-oss:20b, qwen3-vl:4b | Y | - | 0 |  |
| c6_triggered_recovery | c6 | selective_recovery | waypoint | vlm_waypoint | simulated | sim-vlm-dual | - | - | 0 | grid_nav:1 |
| c6g_gemma_recovery | c6g | selective_recovery | waypoint | vlm_point_waypoint | ollama | gemma3:4b | Y | - | 0 | grid_nav_vision:2 |
| c7_aerovla_gemma | c7_aerovla_gemma | direct_vla | direct_vla | aerovla | ollama | gemma3:4b | Y | - | 0 |  |
| c7_aerovla_native | c7_aerovla_native | direct_vla | direct_vla | aerovla | aerovla_hf | XuPeng23/AeroVLA@e37685a, sim-vla | Y | - | 0 |  |
| c7_direct_vla | c7 | direct_vla | direct_vla | mock_vla | simulated | sim-vla | - | - | 0 |  |
| c7t_trained_vla | c7t | direct_vla | direct_vla | learned_visuomotor | simulated | bc-visuomotor | - | - | 0 |  |
| c8_aerovla_gemma | c8_aerovla_gemma | direct_vla | direct_vla | aerovla | ollama | gemma3:4b | Y | - | 0 | grid_nav_aerovla:4 |
| c8_aerovla_native | c8_aerovla_native | direct_vla | direct_vla | aerovla | aerovla_hf | XuPeng23/AeroVLA@e37685a, sim-vla | Y | - | 0 |  |
| c8_aerovla_qwen4_shared | c8_aerovla_qwen4_shared | direct_vla | direct_vla | aerovla | ollama | qwen3-vl:4b | Y | - | 0 | grid_nav_aerovla:2 |
| c8_shielded_vla | c8 | direct_vla | direct_vla | mock_vla | simulated | sim-vla | - | - | 0 | grid_nav:1 |
| c8t_trained_vla_shield | c8t | direct_vla | direct_vla | learned_visuomotor | simulated | bc-visuomotor | - | - | 0 |  |
| c9_vla_history | c9 | direct_vla | direct_vla | mock_vla | simulated | sim-vla | - | - | 0 |  |
| shared_qwen_vla_cached_dev | shared_qwen_vla_cached_dev | direct_vla | direct_vla | shared_qwen_pilot | shared_qwen_vla | qwen3-vl-4b-d207-shared | Y | - | 0 |  |
| shared_qwen_vla_dev | shared_qwen_vla_dev | direct_vla | direct_vla | shared_qwen_pilot | shared_qwen_vla | qwen3-vl-4b-d207-shared | Y | - | 0 |  |
| shared_qwen_vla_first_action_dev | shared_qwen_vla_first_action_dev | direct_vla | direct_vla | shared_qwen_pilot | shared_qwen_vla | qwen3-vl-4b-d207-shared | Y | - | 0 |  |
| vlm_adaptive_plan_gemma_dev | vlm_adaptive_plan_gemma_dev | hybrid_stack | waypoint | adaptive_visual_plan | ollama | gemma4:e2b | Y | - | 0 | grid_nav_onfly_depth_v2_dev:1 |
