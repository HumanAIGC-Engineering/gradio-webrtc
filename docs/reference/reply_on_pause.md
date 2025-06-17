## `ReplyOnPause` Class

```python
ReplyOnPause(
    fn: ReplyFnGenerator,
    startup_fn: Callable | None = None,
    algo_options: AlgoOptions | None = None,
    model_options: ModelOptions | None = None,
    can_interrupt: bool = True,
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
    model: PauseDetectionModel | None = None,
)
```

A stream handler that processes incoming audio, detects pauses, and triggers a reply function (`fn`) when a pause is detected.

This handler accumulates audio chunks, uses a Voice Activity Detection (VAD) model to determine speech segments, and identifies pauses based on configurable thresholds. Once a pause is detected after speech has started, it calls the provided generator function `fn` with the accumulated audio.

It can optionally run a `startup_fn` at the beginning and supports interruption of the reply function if new audio arrives.

### Methods

#### `__init__`

```python
__init__(
    fn: ReplyFnGenerator,
    startup_fn: Callable | None = None,
    algo_options: AlgoOptions | None = None,
    model_options: ModelOptions | None = None,
    can_interrupt: bool = True,
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
    model: PauseDetectionModel | None = None,
)
```

Initializes the ReplyOnPause handler.

**Args:**

| Name                 | Type                                | Description                                                                                              |
| :------------------- | :---------------------------------- | :------------------------------------------------------------------------------------------------------- |
| `fn`                 | `ReplyFnGenerator`                  | The generator function to execute upon pause detection. It receives `(sample_rate, audio_array)` and optionally `*args`. |
| `startup_fn`         | `Callable | None`                  | An optional function to run once at the beginning.                                                       |
| `algo_options`       | `AlgoOptions | None`               | Options for the pause detection algorithm.                                                               |
| `model_options`      | `ModelOptions | None`              | Options for the VAD model.                                                                               |
| `can_interrupt`      | `bool`                              | If True, incoming audio during `fn` execution will stop the generator and process the new audio.         |
| `expected_layout`    | `Literal["mono", "stereo"]`         | Expected input audio layout ('mono' or 'stereo').                                                        |
| `output_sample_rate` | `int`                               | The sample rate expected for audio yielded by `fn`.                                                      |
| `output_frame_size`  | `int | None`                       | Deprecated.                                                                                              |
| `input_sample_rate`  | `int`                               | The expected sample rate of incoming audio.                                                              |
| `model`              | `PauseDetectionModel | None`       | An optional pre-initialized VAD model instance.                                                          |

---

#### `receive`

```python
receive(frame: tuple[int, np.ndarray]) -> None
```

Receives an audio frame from the stream. Processes the audio frame using `process_audio`. If a pause is detected, it sets the event. If interruption is enabled and a reply is ongoing, it closes the current generator and clears the processing queue.

**Args:**

| Name    | Type                   | Description                                                       |
| :------ | :--------------------- | :---------------------------------------------------------------- |
| `frame` | `tuple[int, np.ndarray]` | A tuple containing the sample rate and the audio frame data.      |

---

#### `emit`

```python
emit() -> EmitType | None
```

Produces the next output chunk from the reply generator (`fn`).

This method is called repeatedly after a pause is detected (event is set). If the generator is not already running, it initializes it by calling `fn` with the accumulated audio and any required additional arguments. It then yields the next item from the generator. Handles both sync and async generators. Resets the state upon generator completion or error.

**Returns:**

| Type             | Description                                                                      |
| :--------------- | :------------------------------------------------------------------------------- |
| `EmitType | None` | The next output item from the generator, or None if no pause event has occurred or the generator is exhausted. |

**Raises:**

*   **`Exception`**: Re-raises exceptions occurring within the `fn` generator.

---


#### `start_up`

```python
start_up()
```

Executes the startup function `startup_fn` if provided. Waits for additional arguments if needed before calling `startup_fn`.

---

#### `copy`

```python
copy() -> ReplyOnPause
```

Creates a new instance of ReplyOnPause with the same configuration.

**Returns:**

| Type           | Description                                           |
| :------------- | :---------------------------------------------------- |
| `ReplyOnPause` | A new `ReplyOnPause` instance with identical settings. |

---

#### `determine_pause`

```python
determine_pause(audio: np.ndarray, sampling_rate: int, state: AppState) -> bool
```

Analyzes an audio chunk to detect if a significant pause occurred after speech.

Uses the VAD model to measure speech duration within the chunk. Updates the application state (`state`) regarding whether talking has started and accumulates speech segments.

**Args:**

| Name            | Type         | Description                             |
| :-------------- | :----------- | :-------------------------------------- |
| `audio`         | `np.ndarray` | The numpy array containing the audio chunk. |
| `sampling_rate` | `int`        | The sample rate of the audio chunk.     |
| `state`         | `AppState`   | The current application state.          |

**Returns:**

| Type   | Description                                                                                             |
| :----- | :------------------------------------------------------------------------------------------------------ |
| `bool` | True if a pause satisfying the configured thresholds is detected after speech has started, False otherwise. |

---

#### `process_audio`

```python
process_audio(audio: tuple[int, np.ndarray], state: AppState) -> None
```

Processes an incoming audio frame. Appends the frame to the buffer, runs pause detection on the buffer, and updates the application state.

**Args:**

| Name    | Type                   | Description                                                       |
| :------ | :--------------------- | :---------------------------------------------------------------- |
| `audio` | `tuple[int, np.ndarray]` | A tuple containing the sample rate and the audio frame data.      |
| `state` | `AppState`             | The current application state to update.                          |

---

#### `reset`

```python
reset()
```

Resets the handler state to its initial condition. Clears accumulated audio, resets state flags, closes any active generator, and clears the event flag.

---

#### `trigger_response`

```python
trigger_response()
```

Manually triggers the response generation process. Sets the event flag, effectively simulating a pause detection. Initializes the stream buffer if it's empty.

---



## `ReplyOnStopWords` Class

```python
ReplyOnStopWords(
    fn: ReplyFnGenerator,
    stop_words: list[str],
    startup_fn: Callable | None = None,
    algo_options: AlgoOptions | None = None,
    model_options: ModelOptions | None = None,
    can_interrupt: bool = True,
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
    model: PauseDetectionModel | None = None,
)
```

A stream handler that extends `ReplyOnPause` to trigger based on stop words followed by a pause.

This handler listens to the incoming audio stream, performs Speech-to-Text (STT) to detect predefined stop words. Once a stop word is detected, it waits for a subsequent pause in speech (using the VAD model) before triggering the reply function (`fn`) with the audio recorded *after* the stop word.

### Methods

#### `__init__`

```python
__init__(
    fn: ReplyFnGenerator,
    stop_words: list[str],
    startup_fn: Callable | None = None,
    algo_options: AlgoOptions | None = None,
    model_options: ModelOptions | None = None,
    can_interrupt: bool = True,
    expected_layout: Literal["mono", "stereo"] = "mono",
    output_sample_rate: int = 24000,
    output_frame_size: int | None = None,  # Deprecated
    input_sample_rate: int = 48000,
    model: PauseDetectionModel | None = None,
)
```

Initializes the ReplyOnStopWords handler.

**Args:**

*(Inherits Args from `ReplyOnPause.__init__`)*

| Name         | Type        | Description                                                                                              |
| :----------- | :---------- | :------------------------------------------------------------------------------------------------------- |
| `stop_words` | `list[str]` | A list of strings (words or phrases) to listen for. Detection is case-insensitive and ignores punctuation. |

---

#### `stop_word_detected`

```python
stop_word_detected(text: str) -> bool
```

Checks if any of the configured stop words are present in the text. Performs a case-insensitive search, treating multi-word stop phrases correctly and ignoring basic punctuation.

**Args:**

| Name   | Type   | Description                          |
| :----- | :----- | :----------------------------------- |
| `text` | `str`  | The text transcribed from the audio. |

**Returns:**

| Type   | Description                               |
| :----- | :---------------------------------------- |
| `bool` | True if a stop word is found, False otherwise. |

---

#### `send_stopword`

```python
send_stopword()
```

Sends a 'stopword' message asynchronously via the communication channel (if configured).

---

#### `determine_pause`

```python
determine_pause(audio: np.ndarray, sampling_rate: int, state: ReplyOnStopWordsState) -> bool
```

Analyzes an audio chunk to detect stop words and subsequent pauses. Overrides the `ReplyOnPause.determine_pause` method. First, it performs STT on the audio buffer to detect stop words. Once a stop word is detected (`state.stop_word_detected` is True), it then uses the VAD model to detect a pause in the audio *following* the stop word.

**Args:**

| Name            | Type                    | Description                                          |
| :-------------- | :---------------------- | :--------------------------------------------------- |
| `audio`         | `np.ndarray`            | The numpy array containing the audio chunk.          |
| `sampling_rate` | `int`                   | The sample rate of the audio chunk.                  |
| `state`         | `ReplyOnStopWordsState` | The current application state (ReplyOnStopWordsState). |

**Returns:**

| Type   | Description                                                                                                                            |
| :----- | :------------------------------------------------------------------------------------------------------------------------------------- |
| `bool` | True if a stop word has been detected and a subsequent pause satisfying the configured thresholds is detected, False otherwise.          |

---

#### `reset`

```python
reset()
```

Resets the handler state to its initial condition. Clears accumulated audio, resets state flags (including stop word state), closes any active generator, and clears the event flag.

---

#### `copy`

```python
copy() -> ReplyOnStopWords
```

Creates a new instance of ReplyOnStopWords with the same configuration.

**Returns:**

| Type               | Description                                              |
| :----------------- | :------------------------------------------------------- |
| `ReplyOnStopWords` | A new `ReplyOnStopWords` instance with identical settings. |

*(Inherits other public methods like `start_up`, `process_audio`, `receive`, `trigger_response`, `async_iterate`, `emit` from `ReplyOnPause`)*
