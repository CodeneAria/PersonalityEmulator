# VOICEVOX character
SPEAKER_ID_KASUKABE_TSUMUGI = 8

# personal model name
PERSONALITY_MODEL_NAME = "博麗霊夢"

# Hakurei Reimu
SPEAKER_ID_HAKUREI_REIMU = SPEAKER_ID_KASUKABE_TSUMUGI
VOICE_SPEED_SCALE_HAKUREI_REIMU = 1.2
VOICE_PITCH_SCALE_HAKUREI_REIMU = -0.05

WORD_DICTIONARY_PATH_HAKUREI_REIMU = "./personality/hakurei_reimu/word_dictionary.json"
STORY_SETTINGS_PATH_HAKUREI_REIMU = "./personality/hakurei_reimu/story_settings.json"

# Personality settings
SPEAKER_ID = SPEAKER_ID_HAKUREI_REIMU
VOICE_SPEED_SCALE = VOICE_SPEED_SCALE_HAKUREI_REIMU
VOICE_PITCH_SCALE = VOICE_PITCH_SCALE_HAKUREI_REIMU
WORD_DICTIONARY_PATH = WORD_DICTIONARY_PATH_HAKUREI_REIMU
STORY_SETTINGS_PATH = STORY_SETTINGS_PATH_HAKUREI_REIMU

# LLM Model Settings
PERSONALITY_CORE_SIGNATURE = "[PersonalityCore]"
USE_ELYZA_JP_MODEL = False
if USE_ELYZA_JP_MODEL:
    LLM_MODEL_PATH = "./llm/Llama-3-ELYZA-JP-8B-q4_k_m.gguf"
    LLM_MODEL_DOWNLOAD_PATH = "https://huggingface.co/elyza/Llama-3-ELYZA-JP-8B-GGUF/blob/main/Llama-3-ELYZA-JP-8B-q4_k_m.gguf"
else:
    LLM_MODEL_PATH = "./llm/gemma-3-4b-it-Q4_K_M.gguf"
    LLM_MODEL_DOWNLOAD_PATH = "https://huggingface.co/ggml-org/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf"


LLM_N_CTX = 16384
LLM_N_THREADS = 8
LLM_N_GPU_LAYERS = -1
LLM_SYSTEM_PROMPT = "あなたは優秀なアシスタントです。"

# KoboldCpp (legacy - kept for backward compatibility)
KOBOLD_CPP_CONFIG_FILE_PATH = "./kobold_cpp/config/gemma_mm_kotoba_whisper.kcppt"
# KOBOLD_CPP_CONFIG_FILE_PATH = "./kobold_cpp/config/elyza_jp_kotoba_whisper.kcppt"
KOBOLD_CPP_SIGNATURE = "[KoboldCpp]"
WHISPER_TRANSCRIBE_PREFIX = "Whisper Transcribe Output:"
