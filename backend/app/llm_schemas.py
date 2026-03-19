
ROLE_SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "role": {
            "type": "string",
            "enum": ["Emotional Support", "Clarify Thinking", "Meta Reflection"]
        },
        "confidence": {
            "type": "number"
        },
        "reasons": {
            "type": "string"
        }
    },
    "required": ["role", "confidence", "reasons"],
    "additionalProperties": False
}

EMOTION_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "emotion_label": {
            "type": "string",
            "enum": ["Happy", "Sad", "Anxious", "Angry", "Calm", "Neutral", "Grateful"]
        },
        "confidence": {
            "type": "number"
        },
        "reason": {
            "type": "string"
        }
    },
    "required": ["emotion_label", "confidence", "reason"],
    "additionalProperties": False
}

CRISIS_SCHEMA = {
    "type": "object",
    "properties": {
        "risk_level": {
            "type": "integer",
            "enum": [1, 2, 3]
        },
        "trigger": {
            "type": "string"
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"}
        },
        "confidence": {
            "type": "number"
        }
    },
    "required": ["risk_level", "trigger", "evidence", "confidence"],
    "additionalProperties": False
}

B1_SCHEMA = {
    "type": "object",
    "properties": {
        "reflective_paraphrase": {"type": "string"},
        "implicit_emotion": {"type": "string"},
        "open_question": {"type": "string"},
        "safety_flags": {
            "type": "object",
            "properties": {
                "advice": {"type": "boolean"},
                "diagnosis": {"type": "boolean"},
                "moral_judgement": {"type": "boolean"}
            },
            "required": ["advice", "diagnosis", "moral_judgement"],
            "additionalProperties": False
        }
    },
    "required": [
        "reflective_paraphrase",
        "implicit_emotion",
        "open_question",
        "safety_flags"
    ],
    "additionalProperties": False
}

B2_SCHEMA = {
    "type": "object",
    "properties": {
        "distortion_reflect": {"type": "string"},
        "socratic_question": {"type": "string"},
        "normalization": {"type": "string"},
        "safety_flags": {
            "type": "object",
            "properties": {
                "advice": {"type": "boolean"},
                "diagnosis": {"type": "boolean"},
                "invalidating": {"type": "boolean"}
            },
            "required": ["advice", "diagnosis", "invalidating"],
            "additionalProperties": False
        }
    },
    "required": [
        "distortion_reflect",
        "socratic_question",
        "normalization",
        "safety_flags"
    ],
    "additionalProperties": False
}

B3_SCHEMA = {
    "type": "object",
    "properties": {
        "defusion_metaphor": {"type": "string"},
        "observed_strength": {"type": "string"},
        "value_connection": {"type": "string"},
        "micro_action": {"type": "string"},
        "safety_flags": {
            "type": "object",
            "properties": {
                "advice": {"type": "boolean"},
                "coercive": {"type": "boolean"},
                "diagnosis": {"type": "boolean"}
            },
            "required": ["advice", "coercive", "diagnosis"],
            "additionalProperties": False
        }
    },
    "required": [
        "defusion_metaphor",
        "observed_strength",
        "value_connection",
        "micro_action",
        "safety_flags"
    ],
    "additionalProperties": False
}

INSIGHTS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "emotional_patterns": {"type": "string"},
        "common_themes": {"type": "string"},
        "growth_observations": {"type": "string"},
        "recommendations": {"type": "string"},
        "affirmation": {"type": "string"},
        "focus_points": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": [
        "summary",
        "emotional_patterns",
        "common_themes",
        "growth_observations",
        "recommendations",
        "affirmation",
        "focus_points"
    ],
    "additionalProperties": False
}

# Gating schemas for B1->B2 and B2->B3 transitions
GATING_B1_B2_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["READY_FOR_B2", "STAY_IN_B1"]
        },
        "reason": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {"type": "string"}
        },
        "followup_style": {"type": "string"}
    },
    "required": ["decision", "reason", "evidence", "followup_style"],
    "additionalProperties": False
}

GATING_B2_B3_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["READY_FOR_B3", "STAY_IN_B2"]
        },
        "reason": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {"type": "string"}
        },
        "followup_style": {"type": "string"}
    },
    "required": ["decision", "reason", "evidence", "followup_style"],
    "additionalProperties": False
}
