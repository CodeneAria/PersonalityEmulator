HOSTNAME = "localhost"

# VOICEVOX
VOICEVOX_PORT = 50021
AUDIO_QUERY_ENDPOINT = f"http://{HOSTNAME}:{VOICEVOX_PORT}/audio_query"
SYNTHESIS_ENDPOINT = f"http://{HOSTNAME}:{VOICEVOX_PORT}/synthesis"

SPEAKER_ID_KASUKABE_TSUMUGI = 8

# KoboldCpp
KOBOLDCPP_PORT = 5001
KOBOLDCPP_PATH = "./kobold_cpp"
KOBOLDCPP_EXE_FILE = "koboldcpp"
KOBOLDCPP_DOWNLOAD_URL = "https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp-linux-x64"
KOBOLDCPP_CONFIG_FILE_PATH = "./kobold_cpp/config/starter_jp_voice_input.kcppt"
