"""Local Portuguese neural voice for the race engineer."""
import io
import threading
import wave

from fastapi import FastAPI, Response
from piper import PiperVoice, SynthesisConfig
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI()
voice = PiperVoice.load("/voices/pt_BR-faber-medium.onnx")
lock = threading.Lock()


class RadioAudioRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=480)


@app.post("/audio")
def audio(request: RadioAudioRequest):
    output = io.BytesIO()
    with lock, wave.open(output, "wb") as wav:
        voice.synthesize_wav(request.message, wav, syn_config=SynthesisConfig(length_scale=1.08))
    return Response(content=output.getvalue(), media_type="audio/wav")
