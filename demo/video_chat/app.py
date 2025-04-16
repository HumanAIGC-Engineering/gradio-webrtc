import asyncio
import base64
from io import BytesIO
import json
import math
import queue
import time
from typing import TypedDict
import uuid
import threading

# from fastrtc.utils import Message
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import gradio as gr
import numpy as np
from fastrtc import (
    AsyncAudioVideoStreamHandler,
    WebRTC,
    VideoEmitType,
    AudioEmitType,
)
from PIL import Image
import uvicorn


class Message(TypedDict):
    type: str
    data: any

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

frame_queue = queue.Queue(maxsize=100)

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
        self.video_queue = frame_queue
        self.quit = asyncio.Event()
        self.session = None
        self.last_frame_time = 0

    def copy(self, **kwargs) -> "VideoChatHandler":
        return VideoChatHandler(
            expected_layout=self.expected_layout,
            output_sample_rate=self.output_sample_rate,
            output_frame_size=self.output_frame_size,
        )
    
    def on_pc_connected(self, webrtc_id):
        print(webrtc_id)
    
    chat_id = ''
    async def on_chat_datachannel(self,message: Message,channel): 
      # 返回
      # {"type":"chat",id:"标识属于同一段话", "message":"Hello, world!"}
      # {"type":"avatar_end"} 表示本次对话结束
      if message['type'] == 'stop_chat':
        self.chat_id = ''
        channel.send(json.dumps({'type':'avatar_end'}))
      else:
        id = uuid.uuid4().hex
        self.chat_id = id
        data = message["data"]
        halfLen =  math.floor(data.__len__()/2)
        channel.send(json.dumps({"type":"chat","id":id,"message":data[:halfLen]}))
        await asyncio.sleep(5)
        if self.chat_id == id:
          channel.send(json.dumps({"type":"chat","id":id,"message":data[halfLen:]}))
          channel.send(json.dumps({'type':'avatar_end'}))
    
    async def video_receive(self, frame: np.ndarray):
        # if self.session:
        #     # send image every 1 second
        #     if time.time() - self.last_frame_time > 1:
        #         self.last_frame_time = time.time()
        #         await self.session.send(encode_image(frame))
        #         if self.latest_args[2] is not None:
        #             await self.session.send(encode_image(self.latest_args[2]))
        # print(frame.shape)
        newFrame = np.array(frame)
        newFrame[0:, :, 0] = 255 - newFrame[0:, :, 0]
        # self.video_queue.put_nowait(newFrame)
    
    async def video_emit(self) -> VideoEmitType:
        # print('123123',frame_queue.qsize())
        return frame_queue.get()

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
            avatar_type="",
            avatar_assets_path="",
            avatar_ws_route='/ws',
            elem_id="video-source",
            track_constraints={
                "video": {
                    "facingMode": "user",
                    "width": {"ideal": 500},
                    "height": {"ideal": 500},
                    "frameRate": {"ideal": 30},
                },
                "audio": {
                    "echoCancellation": True,
                    "noiseSuppression": {"exact": True},
                    "autoGainControl": {"exact": False},
                    "sampleRate": {"ideal": 24000},
                    "sampleSize": {"ideal": 16},
                    "channelCount": {"exact": 1},
                },
            }
        )
        handler = VideoChatHandler()
        webrtc.stream(
            handler,
            inputs=[webrtc],
            outputs=[webrtc],
            time_limit=1500,
            concurrency_limit=2,
        )
        # 线程函数：随机生成 numpy 帧
        def generate_frames(width=480, height=960, channels=3):
            while True:
                try:
                    # 随机生成一个 RGB 图像帧
                    frame = np.random.randint(188, 256, (height, width, channels), dtype=np.uint8)
                    
                    # 将帧放入队列
                    frame_queue.put(frame)
                    # print("生成一帧数据，形状:", frame.shape, frame_queue.qsize())
                    
                    # 模拟实时性：避免过度消耗 CPU
                    time.sleep(0.03)  # 每秒约生成 30 帧
                except Exception as e:
                    print(f"生成帧时出错: {e}")
                    break
        thread = threading.Thread(target=generate_frames, daemon=True)
        thread.start()
        
        @demo.app.websocket("/ws")
        async def on_websocket(websocket: WebSocket):
            await websocket.accept()
            while True:
                try:
                    data = await websocket.receive_text()
                    await websocket.send_text(f"Message text was: {data}")
                except WebSocketDisconnect:
                    break

if __name__ == "__main__":
    demo.launch()



