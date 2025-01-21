import asyncio
import base64
import os
import time
from io import BytesIO

import gradio as gr
import numpy as np
from gradio_webrtc import (
    AsyncAudioVideoStreamHandler,
    WebRTC,
    async_aggregate_bytes_to_16bit,
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


class GeminiHandler(AsyncAudioVideoStreamHandler):
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

    def copy(self) -> "GeminiHandler":
        return GeminiHandler(
            expected_layout=self.expected_layout,
            output_sample_rate=self.output_sample_rate,
            output_frame_size=self.output_frame_size,
        )
    
    async def video_receive(self, frame: np.ndarray):
        # if self.session:
        #     # send image every 1 second
        #     if time.time() - self.last_frame_time > 1:
        #         self.last_frame_time = time.time()
        #         await self.session.send(encode_image(frame))
        #         if self.latest_args[2] is not None:
        #             await self.session.send(encode_image(self.latest_args[2]))
        print(frame.shape)
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
#video-source {max-width: 1500px !important; max-height: 600px !important;}
"""

with gr.Blocks(css=css) as demo:

    with gr.Column():
        webrtc = WebRTC(
            width=1500,
            height=500,
            label="Local",
            modality="audio-video",
            mode="send-receive",
            elem_id="video-source",
        )
        webrtc.stream(
            GeminiHandler(),
            inputs=[webrtc],
            outputs=[webrtc],
            time_limit=90,
            concurrency_limit=2,
        )


if __name__ == "__main__":
    demo.launch()
