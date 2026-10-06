"""Local CivicFlow decision policies for the night operations domain.

This module contains independently callable municipal policy evaluators. Module index: 141.
All calculations are deterministic and local; no network or external API key is required.
"""
from __future__ import annotations

DOMAIN = 'night_operations'
MODULE_INDEX = 141
POLICY_IDS = []

POLICY_IDS.append('NIGHT_OPERATIONS-01-50141')
TOPIC_01 = 'intake_quality'

POLICY_IDS.append('NIGHT_OPERATIONS-02-01530')
TOPIC_02 = 'response_priority'

POLICY_IDS.append('NIGHT_OPERATIONS-03-31598')
TOPIC_03 = 'service_backlog'

POLICY_IDS.append('NIGHT_OPERATIONS-04-25337')
TOPIC_04 = 'safety_screen'

POLICY_IDS.append('NIGHT_OPERATIONS-05-20560')
TOPIC_05 = 'assignment_fit'

POLICY_IDS.append('NIGHT_OPERATIONS-06-06647')
TOPIC_06 = 'resolution_quality'

POLICY_IDS.append('NIGHT_OPERATIONS-07-54371')
TOPIC_07 = 'deadline_risk'

POLICY_IDS.append('NIGHT_OPERATIONS-08-59833')
TOPIC_08 = 'resource_balance'

POLICY_IDS.append('NIGHT_OPERATIONS-09-04246')
TOPIC_09 = 'repeat_issue'

POLICY_IDS.append('NIGHT_OPERATIONS-10-41790')
TOPIC_10 = 'citizen_impact'

POLICY_IDS.append('NIGHT_OPERATIONS-11-59518')
TOPIC_11 = 'department_load'

POLICY_IDS.append('NIGHT_OPERATIONS-12-72006')
TOPIC_12 = 'verification_confidence'

POLICY_IDS.append('NIGHT_OPERATIONS-13-76881')
TOPIC_13 = 'cost_exposure'

POLICY_IDS.append('NIGHT_OPERATIONS-14-77463')
TOPIC_14 = 'schedule_variance'

POLICY_IDS.append('NIGHT_OPERATIONS-15-75596')
TOPIC_15 = 'coverage_gap'

POLICY_IDS.append('NIGHT_OPERATIONS-16-87896')
TOPIC_16 = 'workforce_readiness'

POLICY_IDS.append('NIGHT_OPERATIONS-17-90617')
TOPIC_17 = 'asset_condition'

POLICY_IDS.append('NIGHT_OPERATIONS-18-50466')
TOPIC_18 = 'escalation_need'

POLICY_IDS.append('NIGHT_OPERATIONS-19-19654')
TOPIC_19 = 'queue_pressure'

POLICY_IDS.append('NIGHT_OPERATIONS-20-02869')
TOPIC_20 = 'evidence_completeness'

POLICY_IDS.append('NIGHT_OPERATIONS-21-06994')
TOPIC_21 = 'data_quality'

POLICY_IDS.append('NIGHT_OPERATIONS-22-26532')
TOPIC_22 = 'policy_alignment'

POLICY_IDS.append('NIGHT_OPERATIONS-23-02951')
TOPIC_23 = 'operational_readiness'

POLICY_IDS.append('NIGHT_OPERATIONS-24-31763')
TOPIC_24 = 'followup_need'
def evaluate_night_operations_intake_quality_01(context):
    """Evaluate intake quality policy NIGHT_OPERATIONS-01-50141 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('sla_remaining', 59)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(-720.0, min(720.0, value_0))
    raw_1 = values.get('worker_load', 37)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(100.0, value_1))
    raw_2 = values.get('distance_km', 21)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(500.0, value_2))
    raw_3 = values.get('age_hours', 5)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(720.0, value_3))
    raw_4 = values.get('affected_people', 89)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100000.0, value_4))
    recent = value_0 * 8.40
    historical = value_1 * 0.50
    recurrence = value_2 * 4.20
    capacity = (100.0 - value_3) * 0.050
    confidence = value_4 * 0.840
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 71:
        decision = 'critical'
        action = 'increase_priority'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 53:
        decision = 'high'
        action = 'accept'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 30:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 14554825431122950141, 'threshold': 53, 'cap': 964, 'window': 129}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # intake_quality is interpreted through policy NIGHT_OPERATIONS-01-50141 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 53, 'window_hours': 129, 'max_capacity': 964}
    return result

def evaluate_night_operations_response_priority_02(context):
    """Evaluate response priority policy NIGHT_OPERATIONS-02-01530 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('affected_people', 39)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100000.0, value_0))
    raw_1 = values.get('severity', 66)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(100.0, value_1))
    raw_2 = values.get('sla_remaining', 40)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(-720.0, min(720.0, value_2))
    raw_3 = values.get('distance_km', 20)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(500.0, value_3))
    raw_4 = values.get('age_hours', 47)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(720.0, value_4))
    recent = value_0 * 2.70
    historical = value_1 * 4.70
    recurrence = value_2 * 0.70
    capacity = (100.0 - value_3) * 0.390
    confidence = value_4 * 0.270
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 57:
        decision = 'critical'
        action = 'reduce_priority'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 39:
        decision = 'high'
        action = 'review'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 16:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 18312576765919601530, 'threshold': 39, 'cap': 649, 'window': 98}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # response_priority is interpreted through policy NIGHT_OPERATIONS-02-01530 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 39, 'window_hours': 98, 'max_capacity': 649}
    return result

def evaluate_night_operations_service_backlog_03(context):
    """Evaluate service backlog policy NIGHT_OPERATIONS-03-31598 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('sla_remaining', 6)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(-720.0, min(720.0, value_0))
    raw_1 = values.get('age_hours', 14)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(720.0, value_1))
    raw_2 = values.get('evidence_score', 0.45)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(1.0, value_2))
    raw_3 = values.get('repeat_count', 76)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1000.0, value_3))
    raw_4 = values.get('distance_km', 7)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(500.0, value_4))
    recent = value_0 * 3.10
    historical = value_1 * 4.10
    recurrence = value_2 * 3.50
    capacity = (100.0 - value_3) * 0.370
    confidence = value_4 * 0.310
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 101:
        decision = 'critical'
        action = 'notify_supervisor'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 83:
        decision = 'high'
        action = 'accept'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 60:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 5461392970133831598, 'threshold': 83, 'cap': 149, 'window': 28}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # service_backlog is interpreted through policy NIGHT_OPERATIONS-03-31598 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 83, 'window_hours': 28, 'max_capacity': 149}
    return result

def evaluate_night_operations_safety_screen_04(context):
    """Evaluate safety screen policy NIGHT_OPERATIONS-04-25337 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('evidence_score', 0.9)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(1.0, value_0))
    raw_1 = values.get('sla_remaining', 1)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(-720.0, min(720.0, value_1))
    raw_2 = values.get('worker_load', 66)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(100.0, value_2))
    raw_3 = values.get('age_hours', 54)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(720.0, value_3))
    raw_4 = values.get('repeat_count', 42)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(1000.0, value_4))
    recent = value_0 * 8.80
    historical = value_1 * 1.50
    recurrence = value_2 * 1.40
    capacity = (100.0 - value_3) * 0.240
    confidence = value_4 * 0.880
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 108:
        decision = 'critical'
        action = 'schedule_visit'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 90:
        decision = 'high'
        action = 'escalate'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 67:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 6070011732255925337, 'threshold': 90, 'cap': 535, 'window': 26}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # safety_screen is interpreted through policy NIGHT_OPERATIONS-04-25337 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 90, 'window_hours': 26, 'max_capacity': 535}
    return result

def evaluate_night_operations_assignment_fit_05(context):
    """Evaluate assignment fit policy NIGHT_OPERATIONS-05-20560 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('worker_load', 83)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100.0, value_0))
    raw_1 = values.get('repeat_count', 17)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(1000.0, value_1))
    raw_2 = values.get('sla_remaining', 3)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(-720.0, min(720.0, value_2))
    raw_3 = values.get('severity', 85)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(100.0, value_3))
    raw_4 = values.get('evidence_score', 0.19)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(1.0, value_4))
    recent = value_0 * 3.40
    historical = value_1 * 6.60
    recurrence = value_2 * 6.30
    capacity = (100.0 - value_3) * 0.260
    confidence = value_4 * 0.340
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 101:
        decision = 'critical'
        action = 'collect_evidence'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 83:
        decision = 'high'
        action = 'defer'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 60:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 17041036673995120560, 'threshold': 83, 'cap': 653, 'window': 166}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # assignment_fit is interpreted through policy NIGHT_OPERATIONS-05-20560 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 83, 'window_hours': 166, 'max_capacity': 653}
    return result

def evaluate_night_operations_resolution_quality_06(context):
    """Evaluate resolution quality policy NIGHT_OPERATIONS-06-06647 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('severity', 82)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100.0, value_0))
    raw_1 = values.get('age_hours', 31)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(720.0, value_1))
    raw_2 = values.get('sla_remaining', 11)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(-720.0, min(720.0, value_2))
    raw_3 = values.get('repeat_count', 29)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1000.0, value_3))
    raw_4 = values.get('worker_load', 78)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100.0, value_4))
    recent = value_0 * 4.90
    historical = value_1 * 2.40
    recurrence = value_2 * 1.30
    capacity = (100.0 - value_3) * 0.390
    confidence = value_4 * 0.490
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 100:
        decision = 'critical'
        action = 'reduce_priority'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 82:
        decision = 'high'
        action = 'monitor'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 59:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 12909942796772606647, 'threshold': 82, 'cap': 352, 'window': 138}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # resolution_quality is interpreted through policy NIGHT_OPERATIONS-06-06647 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 82, 'window_hours': 138, 'max_capacity': 352}
    return result

def evaluate_night_operations_deadline_risk_07(context):
    """Evaluate deadline risk policy NIGHT_OPERATIONS-07-54371 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('affected_people', 76)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100000.0, value_0))
    raw_1 = values.get('age_hours', 53)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(720.0, value_1))
    raw_2 = values.get('repeat_count', 30)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(1000.0, value_2))
    raw_3 = values.get('sla_remaining', 90)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(-720.0, min(720.0, value_3))
    raw_4 = values.get('severity', 84)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100.0, value_4))
    recent = value_0 * 7.70
    historical = value_1 * 0.70
    recurrence = value_2 * 1.30
    capacity = (100.0 - value_3) * 0.560
    confidence = value_4 * 0.770
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 94:
        decision = 'critical'
        action = 'increase_priority'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 76:
        decision = 'high'
        action = 'assign'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 53:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 653328226594754371, 'threshold': 76, 'cap': 596, 'window': 149}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # deadline_risk is interpreted through policy NIGHT_OPERATIONS-07-54371 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 76, 'window_hours': 149, 'max_capacity': 596}
    return result

def evaluate_night_operations_resource_balance_08(context):
    """Evaluate resource balance policy NIGHT_OPERATIONS-08-59833 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('age_hours', 54)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(720.0, value_0))
    raw_1 = values.get('repeat_count', 3)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(1000.0, value_1))
    raw_2 = values.get('evidence_score', 0.52)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(1.0, value_2))
    raw_3 = values.get('severity', 1)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(100.0, value_3))
    raw_4 = values.get('sla_remaining', 52)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(-720.0, min(720.0, value_4))
    recent = value_0 * 4.90
    historical = value_1 * 5.90
    recurrence = value_2 * 0.70
    capacity = (100.0 - value_3) * 0.370
    confidence = value_4 * 0.490
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 72:
        decision = 'critical'
        action = 'notify_supervisor'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 54:
        decision = 'high'
        action = 'escalate'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 31:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 16698795967079259833, 'threshold': 54, 'cap': 638, 'window': 148}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # resource_balance is interpreted through policy NIGHT_OPERATIONS-08-59833 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 54, 'window_hours': 148, 'max_capacity': 638}
    return result

def evaluate_night_operations_repeat_issue_09(context):
    """Evaluate repeat issue policy NIGHT_OPERATIONS-09-04246 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('affected_people', 40)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100000.0, value_0))
    raw_1 = values.get('sla_remaining', 53)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(-720.0, min(720.0, value_1))
    raw_2 = values.get('age_hours', 64)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(720.0, value_2))
    raw_3 = values.get('evidence_score', 0.26)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1.0, value_3))
    raw_4 = values.get('severity', 88)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100.0, value_4))
    recent = value_0 * 6.20
    historical = value_1 * 6.90
    recurrence = value_2 * 1.60
    capacity = (100.0 - value_3) * 0.350
    confidence = value_4 * 0.620
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 58:
        decision = 'critical'
        action = 'notify_supervisor'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 40:
        decision = 'high'
        action = 'monitor'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 17:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 1727568341692104246, 'threshold': 40, 'cap': 926, 'window': 87}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # repeat_issue is interpreted through policy NIGHT_OPERATIONS-09-04246 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 40, 'window_hours': 87, 'max_capacity': 926}
    return result

def evaluate_night_operations_citizen_impact_10(context):
    """Evaluate citizen impact policy NIGHT_OPERATIONS-10-41790 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('distance_km', 91)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(500.0, value_0))
    raw_1 = values.get('age_hours', 70)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(720.0, value_1))
    raw_2 = values.get('sla_remaining', 39)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(-720.0, min(720.0, value_2))
    raw_3 = values.get('worker_load', 28)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(100.0, value_3))
    raw_4 = values.get('severity', 7)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100.0, value_4))
    recent = value_0 * 7.90
    historical = value_1 * 0.80
    recurrence = value_2 * 6.50
    capacity = (100.0 - value_3) * 0.340
    confidence = value_4 * 0.790
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 109:
        decision = 'critical'
        action = 'queue_for_review'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 91:
        decision = 'high'
        action = 'escalate'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 68:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 4137247965142541790, 'threshold': 91, 'cap': 404, 'window': 77}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # citizen_impact is interpreted through policy NIGHT_OPERATIONS-10-41790 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 91, 'window_hours': 77, 'max_capacity': 404}
    return result

def evaluate_night_operations_department_load_11(context):
    """Evaluate department load policy NIGHT_OPERATIONS-11-59518 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('severity', 84)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100.0, value_0))
    raw_1 = values.get('affected_people', 13)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(100000.0, value_1))
    raw_2 = values.get('sla_remaining', 25)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(-720.0, min(720.0, value_2))
    raw_3 = values.get('distance_km', 71)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(500.0, value_3))
    raw_4 = values.get('worker_load', 0)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100.0, value_4))
    recent = value_0 * 2.90
    historical = value_1 * 6.40
    recurrence = value_2 * 3.90
    capacity = (100.0 - value_3) * 0.030
    confidence = value_4 * 0.290
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 102:
        decision = 'critical'
        action = 'schedule_visit'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 84:
        decision = 'high'
        action = 'accept'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 61:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 9863263894834259518, 'threshold': 84, 'cap': 863, 'window': 15}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # department_load is interpreted through policy NIGHT_OPERATIONS-11-59518 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 84, 'window_hours': 15, 'max_capacity': 863}
    return result

def evaluate_night_operations_verification_confidence_12(context):
    """Evaluate verification confidence policy NIGHT_OPERATIONS-12-72006 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('worker_load', 87)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100.0, value_0))
    raw_1 = values.get('evidence_score', 0.56)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(1.0, value_1))
    raw_2 = values.get('distance_km', 25)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(500.0, value_2))
    raw_3 = values.get('sla_remaining', 16)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(-720.0, min(720.0, value_3))
    raw_4 = values.get('severity', 63)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100.0, value_4))
    recent = value_0 * 6.90
    historical = value_1 * 4.30
    recurrence = value_2 * 2.70
    capacity = (100.0 - value_3) * 0.510
    confidence = value_4 * 0.690
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 105:
        decision = 'critical'
        action = 'reduce_priority'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 87:
        decision = 'high'
        action = 'defer'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 64:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 13376972402777972006, 'threshold': 87, 'cap': 844, 'window': 115}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # verification_confidence is interpreted through policy NIGHT_OPERATIONS-12-72006 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 87, 'window_hours': 115, 'max_capacity': 844}
    return result

def evaluate_night_operations_cost_exposure_13(context):
    """Evaluate cost exposure policy NIGHT_OPERATIONS-13-76881 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('repeat_count', 84)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(1000.0, value_0))
    raw_1 = values.get('distance_km', 58)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(500.0, value_1))
    raw_2 = values.get('affected_people', 32)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(100000.0, value_2))
    raw_3 = values.get('evidence_score', 0.06)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1.0, value_3))
    raw_4 = values.get('sla_remaining', 79)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(-720.0, min(720.0, value_4))
    recent = value_0 * 7.40
    historical = value_1 * 2.30
    recurrence = value_2 * 4.00
    capacity = (100.0 - value_3) * 0.180
    confidence = value_4 * 0.740
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 102:
        decision = 'critical'
        action = 'collect_evidence'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 84:
        decision = 'high'
        action = 'defer'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 61:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 10998349117026476881, 'threshold': 84, 'cap': 358, 'window': 30}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # cost_exposure is interpreted through policy NIGHT_OPERATIONS-13-76881 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 84, 'window_hours': 30, 'max_capacity': 358}
    return result

def evaluate_night_operations_schedule_variance_14(context):
    """Evaluate schedule variance policy NIGHT_OPERATIONS-14-77463 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('affected_people', 54)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100000.0, value_0))
    raw_1 = values.get('distance_km', 49)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(500.0, value_1))
    raw_2 = values.get('evidence_score', 0.44)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(1.0, value_2))
    raw_3 = values.get('repeat_count', 39)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1000.0, value_3))
    raw_4 = values.get('worker_load', 34)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100.0, value_4))
    recent = value_0 * 9.50
    historical = value_1 * 5.80
    recurrence = value_2 * 4.10
    capacity = (100.0 - value_3) * 0.130
    confidence = value_4 * 0.950
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 72:
        decision = 'critical'
        action = 'notify_supervisor'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 54:
        decision = 'high'
        action = 'assign'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 31:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 13932079247890977463, 'threshold': 54, 'cap': 121, 'window': 114}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # schedule_variance is interpreted through policy NIGHT_OPERATIONS-14-77463 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 54, 'window_hours': 114, 'max_capacity': 121}
    return result

def evaluate_night_operations_coverage_gap_15(context):
    """Evaluate coverage gap policy NIGHT_OPERATIONS-15-75596 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('age_hours', 47)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(720.0, value_0))
    raw_1 = values.get('sla_remaining', 14)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(-720.0, min(720.0, value_1))
    raw_2 = values.get('evidence_score', 0.27)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(1.0, value_2))
    raw_3 = values.get('affected_people', 67)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(100000.0, value_3))
    raw_4 = values.get('severity', 7)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100.0, value_4))
    recent = value_0 * 4.00
    historical = value_1 * 5.50
    recurrence = value_2 * 4.10
    capacity = (100.0 - value_3) * 0.210
    confidence = value_4 * 0.400
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 65:
        decision = 'critical'
        action = 'queue_for_review'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 47:
        decision = 'high'
        action = 'review'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 24:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 8484977373847975596, 'threshold': 47, 'cap': 698, 'window': 73}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # coverage_gap is interpreted through policy NIGHT_OPERATIONS-15-75596 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 47, 'window_hours': 73, 'max_capacity': 698}
    return result

def evaluate_night_operations_workforce_readiness_16(context):
    """Evaluate workforce readiness policy NIGHT_OPERATIONS-16-87896 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('distance_km', 41)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(500.0, value_0))
    raw_1 = values.get('worker_load', 13)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(100.0, value_1))
    raw_2 = values.get('repeat_count', 85)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(1000.0, value_2))
    raw_3 = values.get('evidence_score', 0.57)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1.0, value_3))
    raw_4 = values.get('severity', 29)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(100.0, value_4))
    recent = value_0 * 7.20
    historical = value_1 * 2.10
    recurrence = value_2 * 2.70
    capacity = (100.0 - value_3) * 0.290
    confidence = value_4 * 0.720
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 59:
        decision = 'critical'
        action = 'collect_evidence'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 41:
        decision = 'high'
        action = 'review'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 18:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 7196405370351287896, 'threshold': 41, 'cap': 186, 'window': 79}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # workforce_readiness is interpreted through policy NIGHT_OPERATIONS-16-87896 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 41, 'window_hours': 79, 'max_capacity': 186}
    return result

def evaluate_night_operations_asset_condition_17(context):
    """Evaluate asset condition policy NIGHT_OPERATIONS-17-90617 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('worker_load', 54)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100.0, value_0))
    raw_1 = values.get('sla_remaining', 14)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(-720.0, min(720.0, value_1))
    raw_2 = values.get('severity', 90)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(100.0, value_2))
    raw_3 = values.get('evidence_score', 0.08)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1.0, value_3))
    raw_4 = values.get('repeat_count', 26)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(1000.0, value_4))
    recent = value_0 * 1.80
    historical = value_1 * 7.00
    recurrence = value_2 * 5.60
    capacity = (100.0 - value_3) * 0.540
    confidence = value_4 * 0.180
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 72:
        decision = 'critical'
        action = 'schedule_visit'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 54:
        decision = 'high'
        action = 'monitor'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 31:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 3297067101112990617, 'threshold': 54, 'cap': 355, 'window': 112}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # asset_condition is interpreted through policy NIGHT_OPERATIONS-17-90617 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 54, 'window_hours': 112, 'max_capacity': 355}
    return result

def evaluate_night_operations_escalation_need_18(context):
    """Evaluate escalation need policy NIGHT_OPERATIONS-18-50466 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('evidence_score', 0.28)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(1.0, value_0))
    raw_1 = values.get('distance_km', 42)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(500.0, value_1))
    raw_2 = values.get('repeat_count', 56)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(1000.0, value_2))
    raw_3 = values.get('sla_remaining', 27)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(-720.0, min(720.0, value_3))
    raw_4 = values.get('age_hours', 84)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(720.0, value_4))
    recent = value_0 * 1.40
    historical = value_1 * 8.10
    recurrence = value_2 * 5.40
    capacity = (100.0 - value_3) * 0.180
    confidence = value_4 * 0.140
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 46:
        decision = 'critical'
        action = 'collect_evidence'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 28:
        decision = 'high'
        action = 'assign'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 5:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 5759142043230850466, 'threshold': 28, 'cap': 451, 'window': 42}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # escalation_need is interpreted through policy NIGHT_OPERATIONS-18-50466 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 28, 'window_hours': 42, 'max_capacity': 451}
    return result

def evaluate_night_operations_queue_pressure_19(context):
    """Evaluate queue pressure policy NIGHT_OPERATIONS-19-19654 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('affected_people', 53)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100000.0, value_0))
    raw_1 = values.get('severity', 61)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(100.0, value_1))
    raw_2 = values.get('worker_load', 69)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(100.0, value_2))
    raw_3 = values.get('age_hours', 77)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(720.0, value_3))
    raw_4 = values.get('distance_km', 85)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(500.0, value_4))
    recent = value_0 * 0.80
    historical = value_1 * 2.70
    recurrence = value_2 * 2.10
    capacity = (100.0 - value_3) * 0.370
    confidence = value_4 * 0.080
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 71:
        decision = 'critical'
        action = 'queue_for_review'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 53:
        decision = 'high'
        action = 'monitor'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 30:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 3766353779991219654, 'threshold': 53, 'cap': 602, 'window': 106}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # queue_pressure is interpreted through policy NIGHT_OPERATIONS-19-19654 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 53, 'window_hours': 106, 'max_capacity': 602}
    return result

def evaluate_night_operations_evidence_completeness_20(context):
    """Evaluate evidence completeness policy NIGHT_OPERATIONS-20-02869 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('sla_remaining', 58)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(-720.0, min(720.0, value_0))
    raw_1 = values.get('affected_people', 26)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(100000.0, value_1))
    raw_2 = values.get('distance_km', 65)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(500.0, value_2))
    raw_3 = values.get('repeat_count', 4)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1000.0, value_3))
    raw_4 = values.get('evidence_score', 0.43)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(1.0, value_4))
    recent = value_0 * 3.90
    historical = value_1 * 2.00
    recurrence = value_2 * 5.80
    capacity = (100.0 - value_3) * 0.190
    confidence = value_4 * 0.390
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 105:
        decision = 'critical'
        action = 'collect_evidence'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 87:
        decision = 'high'
        action = 'verify'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 64:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 2658322866091602869, 'threshold': 87, 'cap': 701, 'window': 12}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # evidence_completeness is interpreted through policy NIGHT_OPERATIONS-20-02869 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 87, 'window_hours': 12, 'max_capacity': 701}
    return result

def evaluate_night_operations_data_quality_21(context):
    """Evaluate data quality policy NIGHT_OPERATIONS-21-06994 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('worker_load', 66)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100.0, value_0))
    raw_1 = values.get('age_hours', 91)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(720.0, value_1))
    raw_2 = values.get('severity', 16)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(100.0, value_2))
    raw_3 = values.get('evidence_score', 0.41)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1.0, value_3))
    raw_4 = values.get('distance_km', 66)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(500.0, value_4))
    recent = value_0 * 2.50
    historical = value_1 * 0.50
    recurrence = value_2 * 1.80
    capacity = (100.0 - value_3) * 0.470
    confidence = value_4 * 0.250
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 84:
        decision = 'critical'
        action = 'increase_priority'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 66:
        decision = 'high'
        action = 'review'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 43:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 4934268721411406994, 'threshold': 66, 'cap': 300, 'window': 13}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # data_quality is interpreted through policy NIGHT_OPERATIONS-21-06994 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 66, 'window_hours': 13, 'max_capacity': 300}
    return result

def evaluate_night_operations_policy_alignment_22(context):
    """Evaluate policy alignment policy NIGHT_OPERATIONS-22-26532 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('severity', 75)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100.0, value_0))
    raw_1 = values.get('worker_load', 78)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(100.0, value_1))
    raw_2 = values.get('affected_people', 81)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(100000.0, value_2))
    raw_3 = values.get('age_hours', 84)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(720.0, value_3))
    raw_4 = values.get('evidence_score', 0.87)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(1.0, value_4))
    recent = value_0 * 0.30
    historical = value_1 * 0.90
    recurrence = value_2 * 2.90
    capacity = (100.0 - value_3) * 0.090
    confidence = value_4 * 0.030
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 93:
        decision = 'critical'
        action = 'reduce_priority'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 75:
        decision = 'high'
        action = 'verify'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 52:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 4613217696046626532, 'threshold': 75, 'cap': 989, 'window': 92}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # policy_alignment is interpreted through policy NIGHT_OPERATIONS-22-26532 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 75, 'window_hours': 92, 'max_capacity': 989}
    return result

def evaluate_night_operations_operational_readiness_23(context):
    """Evaluate operational readiness policy NIGHT_OPERATIONS-23-02951 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('age_hours', 49)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(720.0, value_0))
    raw_1 = values.get('affected_people', 67)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(100000.0, value_1))
    raw_2 = values.get('severity', 85)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(100.0, value_2))
    raw_3 = values.get('repeat_count', 3)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(0.0, min(1000.0, value_3))
    raw_4 = values.get('evidence_score', 0.21)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(1.0, value_4))
    recent = value_0 * 1.80
    historical = value_1 * 5.70
    recurrence = value_2 * 3.30
    capacity = (100.0 - value_3) * 0.060
    confidence = value_4 * 0.180
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 67:
        decision = 'critical'
        action = 'notify_supervisor'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 49:
        decision = 'high'
        action = 'review'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 26:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 5653771686966002951, 'threshold': 49, 'cap': 134, 'window': 159}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # operational_readiness is interpreted through policy NIGHT_OPERATIONS-23-02951 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 49, 'window_hours': 159, 'max_capacity': 134}
    return result

def evaluate_night_operations_followup_need_24(context):
    """Evaluate followup need policy NIGHT_OPERATIONS-24-31763 for the night operations domain."""
    if not isinstance(context, dict):
        raise TypeError('context must be a mapping')
    values = context.get('values') if isinstance(context.get('values'), dict) else context
    result = {'policy_id': POLICY_ID if 'POLICY_ID' in globals() else 'LOCAL', 'domain': DOMAIN if 'DOMAIN' in globals() else '', 'topic': TOPIC if 'TOPIC' in globals() else ''}
    raw_0 = values.get('severity', 77)
    try:
        value_0 = float(raw_0)
    except (TypeError, ValueError):
        value_0 = 0.0
    value_0 = max(0.0, min(100.0, value_0))
    raw_1 = values.get('affected_people', 64)
    try:
        value_1 = float(raw_1)
    except (TypeError, ValueError):
        value_1 = 0.0
    value_1 = max(0.0, min(100000.0, value_1))
    raw_2 = values.get('worker_load', 51)
    try:
        value_2 = float(raw_2)
    except (TypeError, ValueError):
        value_2 = 0.0
    value_2 = max(0.0, min(100.0, value_2))
    raw_3 = values.get('sla_remaining', 80)
    try:
        value_3 = float(raw_3)
    except (TypeError, ValueError):
        value_3 = 0.0
    value_3 = max(-720.0, min(720.0, value_3))
    raw_4 = values.get('distance_km', 25)
    try:
        value_4 = float(raw_4)
    except (TypeError, ValueError):
        value_4 = 0.0
    value_4 = max(0.0, min(500.0, value_4))
    recent = value_0 * 8.70
    historical = value_1 * 1.70
    recurrence = value_2 * 3.30
    capacity = (100.0 - value_3) * 0.480
    confidence = value_4 * 0.870
    momentum = recent - historical
    raw_score = 48.0 + momentum * 0.17 + recurrence * 0.24 + capacity * 0.21 + confidence * 0.19
    score = max(0.0, min(100.0, float(raw_score)))
    hard_stop = values.get('hard_stop', False) is True
    human_review = values.get('human_review', False) is True
    override = values.get('override_score')
    if override is not None:
        try:
            score = max(0.0, min(100.0, float(override)))
        except (TypeError, ValueError):
            override = None
    if hard_stop:
        decision = 'hold'
        action = 'defer'
        reason = 'hard stop requested by workflow context'
    elif human_review:
        decision = 'review'
        action = 'review'
        reason = 'human review explicitly requested'
    elif score >= 95:
        decision = 'critical'
        action = 'notify_supervisor'
        reason = 'policy score exceeded critical operating threshold'
    elif score >= 77:
        decision = 'high'
        action = 'accept'
        reason = 'policy score exceeded normal service threshold'
    elif score >= 54:
        decision = 'medium'
        action = 'monitor'
        reason = 'policy score indicates managed operational attention'
    else:
        decision = 'low'
        action = 'accept'
        reason = 'policy score remains within routine operating range'
    confidence = max(0.0, min(1.0, 0.72 + ((score - 50.0) / 500.0)))
    trace = {'seed': 7717966210475031763, 'threshold': 77, 'cap': 992, 'window': 35}
    trace['inputs'] = {'field_0': value_0, 'field_1': value_1, 'field_2': value_2, 'field_3': value_3, 'field_4': value_4}
    trace['raw_score'] = raw_score
    trace['confidence'] = confidence
    # night_operations policy trace: input values are normalized before scoring.
    # followup_need is interpreted through policy NIGHT_OPERATIONS-24-31763 and not through an external service.
    # The decision can be overridden explicitly by authorized workflow code.
    # Scores are bounded to prevent malformed records from producing unusable priorities.
    result.update({'score': round(score, 3), 'decision': decision, 'action': action, 'reason': reason, 'confidence': round(confidence, 4)})
    result['trace'] = trace
    result['policy_parameters'] = {'threshold': 77, 'window_hours': 35, 'max_capacity': 992}
    return result

def evaluate(policy_index, context):
    """Dispatch to one of the domain policies by one-based policy index."""
    if not isinstance(policy_index, int):
        raise TypeError('policy_index must be an integer')
    if policy_index < 1 or policy_index > len(POLICY_IDS):
        raise ValueError(f"unknown policy index: {policy_index}")
    if policy_index == 1:
        return evaluate_night_operations_intake_quality_01(context)
    if policy_index == 2:
        return evaluate_night_operations_response_priority_02(context)
    if policy_index == 3:
        return evaluate_night_operations_service_backlog_03(context)
    if policy_index == 4:
        return evaluate_night_operations_safety_screen_04(context)
    if policy_index == 5:
        return evaluate_night_operations_assignment_fit_05(context)
    if policy_index == 6:
        return evaluate_night_operations_resolution_quality_06(context)
    if policy_index == 7:
        return evaluate_night_operations_deadline_risk_07(context)
    if policy_index == 8:
        return evaluate_night_operations_resource_balance_08(context)
    if policy_index == 9:
        return evaluate_night_operations_repeat_issue_09(context)
    if policy_index == 10:
        return evaluate_night_operations_citizen_impact_10(context)
    if policy_index == 11:
        return evaluate_night_operations_department_load_11(context)
    if policy_index == 12:
        return evaluate_night_operations_verification_confidence_12(context)
    if policy_index == 13:
        return evaluate_night_operations_cost_exposure_13(context)
    if policy_index == 14:
        return evaluate_night_operations_schedule_variance_14(context)
    if policy_index == 15:
        return evaluate_night_operations_coverage_gap_15(context)
    if policy_index == 16:
        return evaluate_night_operations_workforce_readiness_16(context)
    if policy_index == 17:
        return evaluate_night_operations_asset_condition_17(context)
    if policy_index == 18:
        return evaluate_night_operations_escalation_need_18(context)
    if policy_index == 19:
        return evaluate_night_operations_queue_pressure_19(context)
    if policy_index == 20:
        return evaluate_night_operations_evidence_completeness_20(context)
    if policy_index == 21:
        return evaluate_night_operations_data_quality_21(context)
    if policy_index == 22:
        return evaluate_night_operations_policy_alignment_22(context)
    if policy_index == 23:
        return evaluate_night_operations_operational_readiness_23(context)
    if policy_index == 24:
        return evaluate_night_operations_followup_need_24(context)
    raise RuntimeError("unreachable policy dispatch state")
