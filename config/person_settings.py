# VOICEVOX
SPEAKER_ID_KASUKABE_TSUMUGI = 8
VOICEVOX_DICTIONARY_PATH = "./voicevox/user_dictionary.json"

# personal model name
PERSONALITY_MODEL_NAME = "博麗霊夢"

# Hakurei Reimu
SPEAKER_ID_HAKUREI_REIMU = SPEAKER_ID_KASUKABE_TSUMUGI
VOICE_SPEED_SCALE_HAKUREI_REIMU = 1.2
VOICE_PITCH_SCALE_HAKUREI_REIMU = -0.05

WORLD_INFO_PATH_HAKUREI_REIMU = "./personality/hakurei_reimu/world_info.md"
PERSON_INFO_PATH_HAKUREI_REIMU = "./personality/hakurei_reimu/person_info.md"
SCENE_SETTINGS_PATH_HAKUREI_REIMU = "./personality/hakurei_reimu/scene_general_talk.json"

# Personality settings
SPEAKER_ID = SPEAKER_ID_HAKUREI_REIMU
VOICE_SPEED_SCALE = VOICE_SPEED_SCALE_HAKUREI_REIMU
VOICE_PITCH_SCALE = VOICE_PITCH_SCALE_HAKUREI_REIMU
WORLD_INFO_PATH = WORLD_INFO_PATH_HAKUREI_REIMU
PERSON_INFO_PATH = PERSON_INFO_PATH_HAKUREI_REIMU
SCENE_SETTINGS_PATH = SCENE_SETTINGS_PATH_HAKUREI_REIMU

# LLM Model Settings
WHISPER_MODEL_NAME = "RoachLin/kotoba-whisper-v2.2-faster"

PERSONALITY_CORE_SIGNATURE = "[PersonalityCore]"
USE_ELYZA_JP_MODEL = True
if USE_ELYZA_JP_MODEL:
    LLM_MODEL_PATH = "./llm/Llama-3-ELYZA-JP-8B-q4_k_m.gguf"
    LLM_MODEL_DOWNLOAD_PATH = "https://huggingface.co/elyza/Llama-3-ELYZA-JP-8B-GGUF/resolve/main/Llama-3-ELYZA-JP-8B-q4_k_m.gguf"
else:
    LLM_MODEL_PATH = "./llm/gemma-3-4b-it-Q4_K_M.gguf"
    LLM_MODEL_DOWNLOAD_PATH = "https://huggingface.co/ggml-org/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf"

LLM_N_CTX = 16384
LLM_N_THREADS = 8
LLM_N_GPU_LAYERS = -1

# Whisper Model Settings
WHISPER_TRANSCRIBE_PREFIX = "Whisper Transcribe Output:"
