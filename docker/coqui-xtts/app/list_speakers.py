from TTS.api import TTS
model = TTS(model_name='tts_models/multilingual/multi-dataset/xtts_v2', progress_bar=False)
print(model.list_speakers())
