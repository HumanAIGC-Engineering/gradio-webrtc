<h1 style='text-align: center; margin-bottom: 1rem'> Gradio WebRTC ⚡️ </h1>

<div style="display: flex; flex-direction: row; justify-content: center">
<img style="display: block; padding-right: 5px; height: 20px;" alt="Static Badge" src="https://img.shields.io/pypi/v/gradio_webrtc"> 
<a href="https://github.com/freddyaboulton/gradio-webrtc" target="_blank"><img alt="Static Badge" style="display: block; padding-right: 5px; height: 20px;" src="https://img.shields.io/badge/github-white?logo=github&logoColor=black"></a>
<a href="https://freddyaboulton.github.io/gradio-webrtc/" target="_blank"><img alt="Static Badge" src="https://img.shields.io/badge/Docs-ffcf40"></a>
</div>

<h3 style='text-align: center'>
Stream video and audio in real time with Gradio using WebRTC.

![picture-in-picture](docs/image.png)
![side-by-side](docs/image2.png)

</h3>

## Installation

```bash
gradio cc install
gradio cc build --no-generate-docs
```

```bash
pip install dist/gradio_webrtc-0.0.30.dev0-py3-none-any.whl
```

## Docs

https://freddyaboulton.github.io/gradio-webrtc/

## Examples

```python
import asyncio
import base64
from io import BytesIO

import gradio as gr
import numpy as np
from gradio_webrtc import (
    AsyncAudioVideoStreamHandler,
    WebRTC,
    VideoEmitType,
    AudioEmitType,
)
from PIL import Image


def encode_audio(data: np.ndarray) -> dict:
    """Encode Audio data to send to the server"""
    return {"mime_type": "audio/pcm", "data": base64.b64encode(data.tobytes()).decode("UTF-8")}


def encode_image(data: np.ndarray) -> dict:
    with BytesIO() as output_bytes:
        pil_image = Image.fromarray(data)
        pil_image.save(output_bytes, "JPEG")
        bytes_data = output_bytes.getvalue()
    base64_str = str(base64.b64encode(bytes_data), "utf-8")
    return {"mime_type": "image/jpeg", "data": base64_str}


class VideoChatHandler(AsyncAudioVideoStreamHandler):
    def __init__(
        self, expected_layout="mono", output_sample_rate=24000, output_frame_size=480
    ) -> None:
        super().__init__(
            expected_layout,
            output_sample_rate,
            output_frame_size,
            input_sample_rate=24000,
        )
        self.audio_queue = asyncio.Queue()
        self.video_queue = asyncio.Queue()
        self.quit = asyncio.Event()
        self.session = None
        self.last_frame_time = 0

    def copy(self) -> "VideoChatHandler":
        return VideoChatHandler(
            expected_layout=self.expected_layout,
            output_sample_rate=self.output_sample_rate,
            output_frame_size=self.output_frame_size,
        )

    async def video_receive(self, frame: np.ndarray):
        newFrame = np.array(frame)
        newFrame[0:, :, 0] = 255 - newFrame[0:, :, 0]
        self.video_queue.put_nowait(newFrame)

    async def video_emit(self) -> VideoEmitType:
        return await self.video_queue.get()

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        frame_size, array = frame
        self.audio_queue.put_nowait(array)

    async def emit(self) -> AudioEmitType:
        if not self.args_set.is_set():
            await self.wait_for_args()
        array = await self.audio_queue.get()
        return (self.output_sample_rate, array)

    def shutdown(self) -> None:
        self.quit.set()
        self.connection = None
        self.args_set.clear()
        self.quit.clear()



css = """
footer {
	display: none !important;
}
"""

with gr.Blocks(css=css) as demo:
        webrtc = WebRTC(
            label="Video Chat",
            modality="audio-video",
            mode="send-receive",
            video_chat=True,
            elem_id="video-source",
        )
        webrtc.stream(
            VideoChatHandler(),
            inputs=[webrtc],
            outputs=[webrtc],
            time_limit=150,
            concurrency_limit=2,
        )


if __name__ == "__main__":
    demo.launch()

```

## Deployment

When deploying in a cloud environment (like Hugging Face Spaces, EC2, etc), you need to set up a TURN server to relay the WebRTC traffic.
The easiest way to do this is to use a service like Twilio.

```python
from twilio.rest import Client
import os

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

client = Client(account_sid, auth_token)

token = client.tokens.create()

rtc_configuration = {
    "iceServers": token.ice_servers,
    "iceTransportPolicy": "relay",
}

with gr.Blocks() as demo:
    ...
    rtc = WebRTC(rtc_configuration=rtc_configuration, ...)
    ...
```
