from rvc.lib.pitch.autopitch import (
    AutoPitch,
    AutoPitchResult,
    VoiceAnalysis,
    VoiceType,
    ModelVoiceType,
    calculate_pitch_shift,
    calc_pitch_shift,  # deprecated, для обратной совместимости
    get_autopitch,
)

__all__ = [
    "AutoPitch",
    "AutoPitchResult", 
    "VoiceAnalysis",
    "VoiceType",
    "ModelVoiceType",
    "calculate_pitch_shift",
    "calc_pitch_shift",
    "get_autopitch",
]
