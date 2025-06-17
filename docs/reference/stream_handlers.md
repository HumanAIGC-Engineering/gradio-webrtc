# Stream Handlers

These abstract base classes define the core interfaces for handling audio and video streams within FastRTC. Concrete handlers like `ReplyOnPause` inherit from these.

## `StreamHandlerBase` Class

```python
StreamHandlerBase(
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
)
```

Base class for handling media streams in FastRTC.

Provides common attributes and methods for managing stream state, communication channels, and basic configuration. This class is intended to be subclassed by concrete stream handlers like `StreamHandler` or `AsyncStreamHandler`.

### Attributes

| Name                 | Type                          | Description                                                              |
| :------------------- | :---------------------------- | :----------------------------------------------------------------------- |
| `expected_layout`    | `Literal["mono", "stereo"]`   | The expected channel layout of the input audio ('mono' or 'stereo').     |
| `output_sample_rate` | `int`                         | The target sample rate for the output audio.                             |
| `output_frame_size`  | `int`                         | The desired number of samples per output audio frame.                    |
| `input_sample_rate`  | `int`                         | The expected sample rate of the input audio.                             |
| `channel`            | `DataChannel \| None`         | The WebRTC data channel for communication.                               |
| `channel_set`        | `asyncio.Event`               | Event indicating if the data channel is set.                             |
| `args_set`           | `asyncio.Event`               | Event indicating if additional arguments are set.                        |
| `latest_args`        | `str \| list[Any]`            | Stores the latest arguments received.                                    |
| `loop`               | `asyncio.AbstractEventLoop`   | The asyncio event loop.                                                  |
| `phone_mode`         | `bool`                        | Flag indicating if operating in telephone mode.                          |

### Methods

#### `__init__`

```python
__init__(
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
)
```

Initializes the StreamHandlerBase.

**Args:**

| Name                 | Type                        | Description                                                          |
| :------------------- | :-------------------------- | :------------------------------------------------------------------- |
| `expected_layout`    | `Literal["mono", "stereo"]` | Expected input audio layout ('mono' or 'stereo').                    |
| `output_sample_rate` | `int`                       | Target output audio sample rate.                                     |
| `output_frame_size`  | `int \| None`               | Deprecated. Frame size is now derived from sample rate.              |
| `input_sample_rate`  | `int`                       | Expected input audio sample rate.                                    |

---

#### `clear_queue`

```python
clear_queue()
```

Clears the internal processing queue via the registered callback.

---

#### `send_message`

```python
async send_message(msg: str)
```

Asynchronously sends a message over the data channel.

**Args:**

| Name  | Type   | Description               |
| :---- | :----- | :------------------------ |
| `msg` | `str`  | The string message to send. |

---

#### `send_message_sync`

```python
send_message_sync(msg: str)
```

Synchronously sends a message over the data channel. Runs the async `send_message` in the event loop and waits for completion.

**Args:**

| Name  | Type   | Description               |
| :---- | :----- | :------------------------ |
| `msg` | `str`  | The string message to send. |

---


#### `reset`

```python
reset()
```

Resets the argument set event.

---

#### `shutdown`

```python
shutdown()
```

Placeholder for shutdown logic. Subclasses can override.

---

## `StreamHandler` Class

```python
StreamHandler(
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
)
```

Abstract base class for synchronous stream handlers.

Inherits from `StreamHandlerBase` and defines the core synchronous interface for processing audio streams. Subclasses must implement `receive`, `emit`, and `copy`.

*(Inherits Attributes and Methods from `StreamHandlerBase`)*

### Abstract Methods

#### `receive`

```python
@abstractmethod
receive(frame: tuple[int, npt.NDArray[np.int16]]) -> None
```

Process an incoming audio frame synchronously.

**Args:**

| Name    | Type                                  | Description                                                              |
| :------ | :------------------------------------ | :----------------------------------------------------------------------- |
| `frame` | `tuple[int, npt.NDArray[np.int16]]` | A tuple containing the sample rate (int) and the audio data as a numpy array (int16). |

---

#### `emit`

```python
@abstractmethod
emit() -> EmitType
```

Produce the next output chunk synchronously. This method is called repeatedly to generate the output to be sent back over the stream.

**Returns:**

| Type       | Description                                                                                                                            |
| :--------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| `EmitType` | An output item conforming to `EmitType`, which could be audio data, additional outputs, control signals (like `CloseStream`), or None. |

---

#### `copy`

```python
@abstractmethod
copy() -> StreamHandler
```

Create a copy of this synchronous stream handler instance. Used to create a new handler for each connection.

**Returns:**

| Type            | Description                                                  |
| :-------------- | :----------------------------------------------------------- |
| `StreamHandler` | A new instance of the concrete StreamHandler subclass.       |

---

#### `start_up`

```python
start_up()
```

Optional synchronous startup logic.

---

## `AsyncStreamHandler` Class

```python
AsyncStreamHandler(
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
)
```

Abstract base class for asynchronous stream handlers.

Inherits from `StreamHandlerBase` and defines the core asynchronous interface using coroutines (`async def`) for processing audio streams. Subclasses must implement `receive`, `emit`, and `copy`. The `start_up` method must also be a coroutine.

*(Inherits Attributes and Methods from `StreamHandlerBase`)*

### Abstract Methods

#### `receive`

```python
@abstractmethod
async receive(frame: tuple[int, npt.NDArray[np.int16]]) -> None
```

Process an incoming audio frame asynchronously.

**Args:**

| Name    | Type                                  | Description                                                              |
| :------ | :------------------------------------ | :----------------------------------------------------------------------- |
| `frame` | `tuple[int, npt.NDArray[np.int16]]` | A tuple containing the sample rate (int) and the audio data as a numpy array (int16). |

---

#### `emit`

```python
@abstractmethod
async emit() -> EmitType
```

Produce the next output chunk asynchronously. This coroutine is called to generate the output to be sent back over the stream.

**Returns:**

| Type       | Description                                                                                                                            |
| :--------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| `EmitType` | An output item conforming to `EmitType`, which could be audio data, additional outputs, control signals (like `CloseStream`), or None. |

---

#### `copy`

```python
@abstractmethod
copy() -> AsyncStreamHandler
```

Create a copy of this asynchronous stream handler instance. Used to create a new handler for each connection.

**Returns:**

| Type                 | Description                                                      |
| :------------------- | :--------------------------------------------------------------- |
| `AsyncStreamHandler` | A new instance of the concrete AsyncStreamHandler subclass.      |

---

#### `start_up`

```python
async start_up()
```

Optional asynchronous startup logic. Must be a coroutine (`async def`).

---

## `AudioVideoStreamHandler` Class

```python
AudioVideoStreamHandler(
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
)
```

Abstract base class for synchronous handlers processing both audio and video.

Inherits from `StreamHandler` (synchronous audio) and adds abstract methods for handling video frames synchronously. Subclasses must implement the audio methods (`receive`, `emit`) and the video methods (`video_receive`, `video_emit`), as well as `copy`.

*(Inherits Attributes and Methods from `StreamHandler`)*

### Abstract Methods

#### `video_receive`

```python
@abstractmethod
video_receive(frame: VideoFrame) -> None
```

Process an incoming video frame synchronously.

**Args:**

| Name    | Type         | Description                   |
| :------ | :----------- | :---------------------------- |
| `frame` | `VideoFrame` | The incoming aiortc `VideoFrame`. |

---

#### `video_emit`

```python
@abstractmethod
video_emit() -> VideoEmitType
```

Produce the next output video frame synchronously.

**Returns:**

| Type            | Description                                                                                              |
| :-------------- | :------------------------------------------------------------------------------------------------------- |
| `VideoEmitType` | An output item conforming to `VideoEmitType`, typically a numpy array representing the video frame, or None. |

---

#### `copy`

```python
@abstractmethod
copy() -> AudioVideoStreamHandler
```

Create a copy of this audio-video stream handler instance.

**Returns:**

| Type                    | Description                                                          |
| :---------------------- | :------------------------------------------------------------------- |
| `AudioVideoStreamHandler` | A new instance of the concrete AudioVideoStreamHandler subclass.       |

---

## `AsyncAudioVideoStreamHandler` Class

```python
AsyncAudioVideoStreamHandler(
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
)
```

Abstract base class for asynchronous handlers processing both audio and video.

Inherits from `AsyncStreamHandler` (asynchronous audio) and adds abstract coroutines for handling video frames asynchronously. Subclasses must implement the async audio methods (`receive`, `emit`, `start_up`) and the async video methods (`video_receive`, `video_emit`), as well as `copy`.

*(Inherits Attributes and Methods from `AsyncStreamHandler`)*

### Abstract Methods

#### `video_receive`

```python
@abstractmethod
async video_receive(frame: npt.NDArray[np.float32]) -> None
```

Process an incoming video frame asynchronously.

**Args:**

| Name    | Type                     | Description                                                                                              |
| :------ | :----------------------- | :------------------------------------------------------------------------------------------------------- |
| `frame` | `npt.NDArray[np.float32]` | The video frame data as a numpy array (float32). Note: The type hint differs from the synchronous version. |

---

#### `video_emit`

```python
@abstractmethod
async video_emit() -> VideoEmitType
```

Produce the next output video frame asynchronously.

**Returns:**

| Type            | Description                                                                                              |
| :-------------- | :------------------------------------------------------------------------------------------------------- |
| `VideoEmitType` | An output item conforming to `VideoEmitType`, typically a numpy array representing the video frame, or None. |

---

#### `copy`

```python
@abstractmethod
copy() -> AsyncAudioVideoStreamHandler
```

Create a copy of this asynchronous audio-video stream handler instance.

**Returns:**

| Type                         | Description                                                              |
| :--------------------------- | :----------------------------------------------------------------------- |
| `AsyncAudioVideoStreamHandler` | A new instance of the concrete AsyncAudioVideoStreamHandler subclass.      |
