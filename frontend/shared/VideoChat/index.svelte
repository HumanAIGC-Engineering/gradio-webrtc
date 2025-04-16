<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";
  import type { ComponentType } from "svelte";

  import {
    CameraOff,
    CameraOn,
    Check,
    PictureInPicture,
    Send,
    SideBySide,
    VolumeOff,
    VolumeOn,
    SubtitleOn,
    SubtitleOff,
    MicOff,
    MicOn,
  } from "./icons";
  import type { I18nFormatter } from "@gradio/utils";
  import { Spinner } from "@gradio/icons";
  import WebcamPermissions from "../WebcamPermissions.svelte";
  import { fade } from "svelte/transition";
  import {
    createSimulatedAudioTrack,
    createSimulatedVideoTrack,
    get_devices,
    get_stream,
    set_available_devices,
    set_local_stream,
  } from "../VideoChat/stream_utils";
  import { start, stop } from "./webrtc_utils";
  import { derived } from "svelte/store";
  import ChatInput from "./components/ChatInput.svelte";
  import ChatBtn from "./components/ChatBtn.svelte";
  import ChatMessage from "./components/ChatMessage.svelte";
  import { click_outside } from "./utils";
  import { GaussianAvatar } from "./gaussianAvatar";
  import { WS } from "./helpers/ws";
  import { WsEventTypes } from "./interface/eventType";
  import ChatRecords from "./components/ChatRecords.svelte";

  let available_video_devices: MediaDeviceInfo[] = [];
  let available_audio_devices: MediaDeviceInfo[] = [];
  let selected_video_device: MediaDeviceInfo | null = null;
  let selected_audio_device: MediaDeviceInfo | null = null;
  let stream_state: "open" | "waiting" | "closed" = "closed";
  export let on_change_cb: (msg: "tick" | "change") => void;
  export let rtp_params: RTCRtpParameters = {} as RTCRtpParameters;
  export let button_labels: { start: string; stop: string; waiting: string };
  export let height: number | undefined;
  export let avatar_type: "" | "gs" = "";
  export let avatar_ws_route: string = "";
  export let avatar_assets_path: string = "";

  export const modify_stream: (state: "open" | "closed" | "waiting") => void = (
    state: "open" | "closed" | "waiting",
  ) => {
    if (state === "closed") {
      stream_state = "closed";
    } else if (state === "waiting") {
      stream_state = "waiting";
    } else {
      stream_state = "open";
    }
  };

  export let track_constraints: MediaTrackConstraints | null = null;
  export let rtc_configuration: Object;
  export let stream_every = 1;
  export let server: {
    offer: (body: any) => Promise<any>;
  };
  export let i18n: I18nFormatter;

  $: websocketMode = !!avatar_type;
  let canvasRef: HTMLCanvasElement;
  let ws: WS | undefined;
  function initWebsocket(ws_route) {
    ws = new WS(
      `${window.location.protocol.includes("https") ? "wss" : "ws"}://${window.location.host}${ws_route}/${webrtc_id}`,
    );
    ws.on(WsEventTypes.WS_OPEN, () => {
      console.log("socket opened");
    });
    ws.on(WsEventTypes.WS_CLOSE, () => {
      console.log("socket closed");
    });
    ws.on(WsEventTypes.WS_ERROR, (event) => {
      console.log("socket error", event);
    });
    ws.on(WsEventTypes.WS_MESSAGE, (data) => {
      console.log("socket on message", data);
    });
  }

  let localAvatarRenderer = null;

  let volumeMuted = false;
  let micMuted = false;
  let cameraOff = false;
  const handle_volume_mute = () => {
    volumeMuted = !volumeMuted;
    if (avatar_type === "gs") {
      localAvatarRenderer?.setAvatarMute(volumeMuted);
    }
  };
  const handle_mic_mute = () => {
    micMuted = !micMuted;
    stream.getTracks().forEach((track) => {
      if (track.kind.includes("audio")) track.enabled = !micMuted;
    });
  };
  const handle_camera_off = () => {
    cameraOff = !cameraOff;
    stream.getTracks().forEach((track) => {
      if (track.kind.includes("video")) track.enabled = !cameraOff;
    });
  };

  const dispatch = createEventDispatcher<{
    tick: undefined;
    error: string;
    start_recording: undefined;
    stop_recording: undefined;
    close_stream: undefined;
  }>();
  const fillStream = async (
    audioDeviceId: string,
    videoDeviceId: string,
    devices,
    node,
  ) => {
    hasMic = devices.some((device) => {
            return device.kind === "audioinput" && device.deviceId;
          }) && hasMicPermission
    hasCamera = devices.some(
      (device) => device.kind === "videoinput" && device.deviceId,
    ) && hasCameraPermission
    await get_stream(
      audioDeviceId && audioDeviceId !== "default"
        ? { deviceId: { exact: audioDeviceId } }
        : hasMic,
      videoDeviceId && videoDeviceId !== "default"
        ? { deviceId: { exact: videoDeviceId } }
        : hasCamera,
      node,
      track_constraints,
    )
      .then(async (local_stream) => {
        stream = local_stream;
        update_available_devices();
        console.log(available_video_devices, "available_video_devices");
        console.log(available_audio_devices, "available_audio_devices");
      })
      .then(() => {
        const used_devices = stream
          .getTracks()
          .map((track) => track.getSettings()?.deviceId);
        used_devices.forEach((device_id) => {
          const used_device = devices.find(
            (device) => device.deviceId === device_id,
          );
          if (used_device && used_device?.kind.includes("video")) {
            selected_video_device = used_device;
          } else if (used_device && used_device?.kind.includes("audio")) {
            selected_audio_device = used_device;
          }
        });
        !selected_video_device &&
          (selected_video_device = available_video_devices[0]);
      })
      .catch((e) => {
        console.error(i18n("image.no_webcam_support"), e);
      })
      .finally(() => {
        console.log(stream);
        if (!stream) {
          stream = new MediaStream();
        }
        console.log(stream.getTracks());

        if (!stream.getTracks().find((item) => item.kind === "audio")) {
          stream.addTrack(createSimulatedAudioTrack());
        }
        if (!stream.getTracks().find((item) => item.kind === "video")) {
          stream.addTrack(createSimulatedVideoTrack());
        }
        console.log(hasCamera, hasMic);
        webcam_accessed = true;
        local_stream = stream;
        set_local_stream(local_stream, node);
      });
  };
  const handle_device_change = async (deviceId: string): Promise<void> => {
    const device_id = deviceId;
    console.log(deviceId, selected_audio_device, selected_video_device);
    const devices = await get_devices();

    console.log("🚀 ~ handle_device_change ~ devices:", devices);
    let videoDeviceId =
      selected_video_device &&
      devices.some(
        (device) => device.deviceId === selected_video_device.deviceId,
      )
        ? selected_video_device.deviceId
        : "";
    let audioDeviceId =
      selected_audio_device &&
      devices.some(
        (device) => device.deviceId === selected_audio_device.deviceId,
      )
        ? selected_audio_device.deviceId
        : "";
    if (
      available_audio_devices.find(
        (audio_device) => audio_device.deviceId === device_id,
      )
    ) {
      audioDeviceId = device_id;
      micListShow = false;
      micMuted = false;
    } else if (
      available_video_devices.find(
        (video_device) => video_device.deviceId === device_id,
      )
    ) {
      videoDeviceId = device_id;
      cameraListShow = false;
      cameraOff = false;
    }
    const node = localVideoRef;
    fillStream(audioDeviceId, videoDeviceId, devices, node);
  };
  let hasCamera = true;
  let hasCameraPermission = true
  let hasMic = true;
  let hasMicPermission = true // 部分设备上无法通过设备列表判断
  async function update_available_devices() {
    const devices = await get_devices();
    available_video_devices = set_available_devices(devices, "videoinput");
    available_audio_devices = set_available_devices(devices, "audioinput");
  }
  async function access_webcam(): Promise<void> {
    try {
      const node = localVideoRef;
      micMuted = false;
      cameraOff = false;
      volumeMuted = false;

      await navigator.mediaDevices
        .getUserMedia({
          audio: true,
        })
        .catch(() => {
          console.log('no audio permission')
          hasMicPermission = false
        });
      await navigator.mediaDevices
        .getUserMedia({
          video: true,
        })
        .catch(() => {
          console.log('no video permission')
          hasCameraPermission = false
        });
      const devices = await get_devices();
      console.log("🚀 ~ access_webcam ~ devices:", devices);
      let videoDeviceId =
        selected_video_device &&
        devices.some(
          (device) => device.deviceId === selected_video_device.deviceId,
        )
          ? selected_video_device.deviceId
          : "";
      let audioDeviceId =
        selected_audio_device &&
        devices.some(
          (device) => device.deviceId === selected_audio_device.deviceId,
        )
          ? selected_audio_device.deviceId
          : "";
      console.log(videoDeviceId, audioDeviceId, " access web device");
      fillStream(audioDeviceId, videoDeviceId, devices, node);

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        dispatch("error", i18n("image.no_webcam_support"));
        alert(i18n("image.no_webcam_support"));
      }
    } catch (err) {
      if (err instanceof DOMException && err.name == "NotAllowedError") {
        dispatch("error", i18n("image.allow_webcam_access"));
      } else {
        throw err;
      }
    }
  }

  let recording = false;
  let stream: MediaStream;
  let local_stream: MediaStream;

  let webcam_accessed = false;
  let webcam_received = false;
  let pc: RTCPeerConnection;
  export let webrtc_id;

  export let wave_color: string = "#7873F6";

  const audio_source_callback = () => {
    if (local_stream) return local_stream;
    else return localVideoRef.srcObject as MediaStream;
  };

  let replying = false;
  let chat_data_channel;
  function on_interrupt() {
    if (chat_data_channel) {
      chat_data_channel.send(JSON.stringify({ type: "stop_chat" }));
    }
  }
  function on_send(message: string) {
    if (!message) return
    chat_data_channel.send(JSON.stringify({ type: "chat", data: message }));
    replying = true;
    chatRecordsInstance?.expose?.scrollToBottom()
  }
  let inlineDisplayChatRecords = true
  let showChatRecords = false;
  function handle_subtitle_toggle(){
    showChatRecords = !showChatRecords
    computeRemotePosition()
  }
  let chatRecordsInstance
  let chatRecords: Array<{ id: string; role: 'human'|'avatar'; message: string }> = [];
  function on_channel_message(event: any) {
    const data = JSON.parse(event.data);
    if (data.type === "chat") {
      const index =  chatRecords.findIndex(item => {
        return item.id === data.id
      })
      if (index!==-1) {
        const item = chatRecords[index]
        item.message += data.message;
        chatRecords.splice(index,1,item)
        chatRecords = [...chatRecords]
      }else{
        chatRecords = [...chatRecords,{
          id: data.id,
          role: data.role || 'human', // TODO: 默认值测试后续删除
          message: data.message
        }];
      }
    } else if (data.type === "avatar_end") {
      replying = false;
    }
  }
  function computeChatRecordsPosition(){
    if(videoShowType === "side-by-side"){
      inlineDisplayChatRecords = true
      return
    }
    const containerWidth = wrapperRef.offsetWidth
    const remoteVideoWidth = remoteVideoPosition.width
    inlineDisplayChatRecords = (remoteVideoWidth+46)>(containerWidth/2)
  }
  async function start_webrtc(): Promise<void> {
    if (stream_state === "closed") {
      chatRecords = []
      pc = new RTCPeerConnection(rtc_configuration);
      pc.addEventListener("connectionstatechange", async (event) => {
        switch (pc.connectionState) {
          case "connected":
            stream_state = "open";
            break;
          case "disconnected":
            stream_state = "closed";
            stop(pc);
            await access_webcam();
            break;
          default:
            break;
        }
      });
      stream_state = "waiting";
      webrtc_id = Math.random().toString(36).substring(2);
      start(
        stream,
        pc,
        remoteVideoRef,
        server.offer,
        webrtc_id,
        "video",
        on_change_cb,
        rtp_params,
      )
        .then(([connection, datachannel]) => {
          pc = connection;
          webcam_received = true;
          onplayingRemoteVideo()

          chat_data_channel = datachannel;

          chat_data_channel.addEventListener("message", on_channel_message);
          if (avatar_type) {
            initWebsocket(avatar_ws_route);
          }
          if (avatar_type === "gs") {
            localAvatarRenderer = doGaussianRender();
          }
        })
        .catch(() => {
          console.info("catching");
          stream_state = "closed";
          webcam_received = false;
          dispatch("error", "Too many concurrent users. Come back later!");
        });
    } else if (stream_state === "waiting") {
      // waiting 中不允许操作
      return;
    } else {
      replying = false;
      remoteVideoPosition.init = false;
      computeLocalPosition();
      stop(pc);
      stream_state = "closed";
      webcam_received = false;
      chatRecords = []
      await access_webcam();
      if (avatar_type === "gs") {
        localAvatarRenderer?.exit();
        gsLoadPercent = 0;
      }
    }
  }
  console.log("avatar", avatar_assets_path, avatar_type, avatar_ws_route);
  let gsLoadPercent = 0;
  function doGaussianRender() {
    const gaussianAvatar = new GaussianAvatar({
      container: remoteVideoContainerRef,
      assetsPath: avatar_assets_path,
      ws: ws,
      loadProgress: (progress) => {
        console.log('gs loadProgress', progress)
        gsLoadPercent = progress;
        if (progress >= 1) {
          computeRemotePosition();
        }
      },
    });
    gaussianAvatar.start();
    return gaussianAvatar;
  }

  let assetLoaded = true
  $: if (avatar_type === 'gs') {
     assetLoaded = gsLoadPercent >= 1
    }


  let wrapperRef: HTMLDivElement;
  const wrapperRect = {
    width: 0,
    height: 0,
  };
  let videoShowType: "side-by-side" | "picture-in-picture" =
    "picture-in-picture";
  $: isSideBySide = videoShowType === "side-by-side";
  $: isPictureInPicture = videoShowType === "picture-in-picture";
  let localVideoRef: HTMLVideoElement;
  let localVideoContainerRef: HTMLDivElement;
  let localVideoPosition = {
    left: 10,
    top: 0,
    width: 1,
    height: 1,
    init: false,
  };
  let remoteVideoRef: HTMLVideoElement;
  let remoteVideoContainerRef: HTMLDivElement;
  let remoteVideoPosition = {
    left: 0,
    top: 0,
    width: 1,
    height: 1,
    init: false,
  };
  let chatInputPosition = {
    left: 0,
    top: 0,
    width: 1,
    height: 1,
  };
  let actionsPosition = {
    left: 0,
    bottom: 0,
    init: false,
    isOverflow: false,
    isOnVideoTop: false
  };

  // remoteVideoPosition

  // const computeVideoPosition = () => {

  // }
  // deal with dom events
  onMount(() => {
    wrapperRef.getBoundingClientRect();
    wrapperRect.width = wrapperRef.clientWidth;
    wrapperRect.height = wrapperRef.clientHeight;
    isLandScape = wrapperRect.width * 1.5 > wrapperRect.height;
    console.log(wrapperRect);
  });

  function changeVideoShowType() {
    if (videoShowType === "picture-in-picture") {
      videoShowType = "side-by-side";
    } else if (videoShowType === "side-by-side") {
      videoShowType = "picture-in-picture";
    }
    computeRemotePosition()
    computeChatRecordsPosition()
    computeRemotePosition()
  }
  function computeChatInputPosition() {
    const newPosition = remoteVideoPosition.init
      ? remoteVideoPosition
      : localVideoPosition;
    chatInputPosition.left = newPosition.left;
    chatInputPosition.width = newPosition.width;
  }
  function computeLocalPosition() {
    if (!localVideoRef || !localVideoContainerRef || !localVideoRef.videoHeight)
      return;
    if (remoteVideoPosition.init) {
      // 存在远端视频则计算画中画
      // let height = remoteVideoPosition.height / 4;
      // let width =
      //   (height / localVideoRef.videoHeight) * localVideoRef.videoWidth;
      let width = remoteVideoPosition.width / 2;
      let height =
        (width / localVideoRef.videoWidth) * localVideoRef.videoHeight;
      localVideoPosition.left = remoteVideoPosition.left + 14;
      localVideoPosition.top =
        remoteVideoPosition.top + remoteVideoPosition.height - height - 14;
      localVideoPosition.width = width;
      localVideoPosition.height = height;

      actionsPosition.left =
        remoteVideoPosition.left + remoteVideoPosition.width + 10;
      console.log(
        "----------",
        actionsPosition.left > wrapperRect.width,
        actionsPosition.left,
        wrapperRect.width,
      );

      if(actionsPosition.left + 46 > wrapperRect.width){
        actionsPosition.left =
         actionsPosition.left - 60
        actionsPosition.isOnVideoTop = true
      }else{
        actionsPosition.isOnVideoTop = false
      }
      actionsPosition.bottom =
        wrapperRect.height -
        remoteVideoPosition.top -
        remoteVideoPosition.height +
        5;
      actionsPosition.isOverflow =
        actionsPosition.left + 300 > wrapperRect.width;
    } else {
      // 否则则占用全屏
      let height = wrapperRect.height - 24;
      let width =
        (height / localVideoRef.videoHeight) * localVideoRef.videoWidth;
      width > wrapperRect.width && (width = wrapperRect.width);
      localVideoPosition.left = (wrapperRect.width - width) / 2;
      localVideoPosition.top = wrapperRect.height - height;
      localVideoPosition.width = width;
      localVideoPosition.height = height;

      actionsPosition.left =
        localVideoPosition.left + localVideoPosition.width + 10;
      actionsPosition.left =
        actionsPosition.left > wrapperRect.width
          ? actionsPosition.left - 60
          : actionsPosition.left;
      actionsPosition.bottom =
        wrapperRect.height -
        localVideoPosition.top -
        localVideoPosition.height +
        5;
      actionsPosition.isOverflow =
        actionsPosition.left + 300 > wrapperRect.width;
    }
    computeChatInputPosition();
  }
  function onplayingRemoteVideo(){
    computeRemotePosition() // 先计算出视频宽度
    computeChatRecordsPosition() // 根据宽度更新inlineDisplayChatRecords标记
    computeRemotePosition() // 再次根据标记计算出left
  }
  function computeRemotePosition() {
    if(stream_state !== 'open' && !websocketMode) return
    let height = wrapperRect.height - 24;
    let width = 0;
    if (websocketMode) {
      width = (height / 16) * 9;
      width > wrapperRect.width && (width = wrapperRect.width);
    } else {
      if (!remoteVideoRef.srcObject || !remoteVideoRef.videoHeight) return;
      console.log(
        remoteVideoRef.videoHeight,
        remoteVideoRef.videoWidth,
        "---------------------",
      );
      width = (height / remoteVideoRef.videoHeight) * remoteVideoRef.videoWidth;
      width > wrapperRect.width && (width = wrapperRect.width);
    }
    if(showChatRecords && !inlineDisplayChatRecords){
      remoteVideoPosition.left = (wrapperRect.width) / 2 - width;
    }else{
      remoteVideoPosition.left = (wrapperRect.width - width) / 2;
    }
    remoteVideoPosition.top = wrapperRect.height - height;
    remoteVideoPosition.width = width;
    remoteVideoPosition.height = height;
    remoteVideoPosition.init = true;
    computeLocalPosition();
  }
  let micListShow = false;
  let cameraListShow = false;
  function open_mic_list(e) {
    micListShow = true;
    e.preventDefault();
    e.stopPropagation();
  }
  function open_camera_list(e) {
    cameraListShow = true;
    e.preventDefault();
    e.stopPropagation();
  }
  export let isLandScape = true;
  window.addEventListener("resize", () => {
    wrapperRef.getBoundingClientRect();
    wrapperRect.width = wrapperRef.clientWidth;
    wrapperRect.height = wrapperRef.clientHeight;
    isLandScape = wrapperRect.width * 1.5 > wrapperRect.height;
    computeLocalPosition();
    computeRemotePosition();
    computeChatRecordsPosition();
    computeRemotePosition()
  });

  $: actionsOnBottom = !actionsPosition.isOnVideoTop||!showChatRecords||showChatRecords && !inlineDisplayChatRecords 
</script>

<div class="wrap" style:height={height > 100 ? "100%" : "90vh"}>
  <!-- svelte-ignore a11y-missing-attribute -->
  {#if !webcam_accessed}
    <div in:fade={{ delay: 100, duration: 200 }} style="height: 100%">
      <WebcamPermissions on:click={async () => access_webcam()} />
    </div>
  {/if}
  <div
    class="video-container"
    bind:this={wrapperRef}
    class:vertical={!isLandScape}
    class:picture-in-picture={isPictureInPicture}
    class:side-by-side={isSideBySide}
    class:no-local-video={!hasCamera || cameraOff}
    style:visibility={webcam_accessed ? "visible" : "hidden"}
  >
    <div
      class="local-video-container"
      style:display={(!hasCamera && stream_state === "open") || cameraOff
        ? "none"
        : "block"}
      bind:this={localVideoContainerRef}
      style:left={localVideoPosition.width < 10
        ? "50%"
        : localVideoPosition.left + "px"}
      style:top={localVideoPosition.height < 10
        ? "50%"
        : localVideoPosition.top + "px"}
      style:width={isPictureInPicture ? localVideoPosition.width + "px" : ""}
      style:height={isPictureInPicture ? localVideoPosition.height + "px" : ""}
    >
      <video
        style:display={!hasCamera || cameraOff ? "none" : "block"}
        class="local-video"
        on:playing={computeLocalPosition}
        bind:this={localVideoRef}
        autoplay
        muted
        playsinline
        style:visibility={isPictureInPicture && cameraOff
          ? "hidden"
          : "visible"}
      />
    </div>
    <div
      class="remote-video-container"
      bind:this={remoteVideoContainerRef}
      style:left={remoteVideoPosition.width < 10
        ? "50%"
        : remoteVideoPosition.left + "px"}
      style:top={remoteVideoPosition.height < 10
        ? "50%"
        : remoteVideoPosition.top + "px"}
      style:width={isPictureInPicture ? remoteVideoPosition.width + "px" : ""}
      style:height={isPictureInPicture ? remoteVideoPosition.height + "px" : ""}
    >
      <!-- {#if websocketMode}
      <canvas bind:this={canvasRef} class="remote-canvas" height={remoteVideoPosition.height} width={remoteVideoPosition.width} ></canvas>
    {:else} -->
    {#if !websocketMode}
      <video
        class="remote-video"
        style:display={stream_state === 'open'?'block':'none'}
        on:playing={onplayingRemoteVideo}
        bind:this={remoteVideoRef}
        autoplay
        playsinline
        muted={volumeMuted}
      />
      
    {/if}
    {#if stream_state === "open" && showChatRecords && inlineDisplayChatRecords}
        <div class="chat-records-container" style={!hasCamera || cameraOff?'width:80%;padding-bottom:12px;':'padding-bottom:12px;'}>
          <ChatRecords bind:this={chatRecordsInstance} chatRecords={chatRecords.filter((_, index) => index >= chatRecords.length - 4)}></ChatRecords>
        </div>
      {/if}
    </div>
    {#if stream_state === "open" && showChatRecords && !inlineDisplayChatRecords}
    <!-- ${remoteVideoPosition.left+remoteVideoPosition.width+46+12+16}px -->
    <div class="chat-records-container" style={`right: calc(50% - 60px); transform:translate(100%); width:${remoteVideoPosition.width}px; height: ${remoteVideoPosition.height}px;`}>
      <ChatRecords bind:this={chatRecordsInstance} {chatRecords}></ChatRecords>
    </div>
  {/if}
    <div
      class="actions"
      style:left={isPictureInPicture ? actionsPosition.left + "px" : ""}
      style:bottom={isPictureInPicture && actionsOnBottom  ? actionsPosition.bottom + "px" : ""}
      style:top={isPictureInPicture && !actionsOnBottom  ? remoteVideoPosition.top+12+'px' : ""}
    >
      <div class="action-group">
        <!-- svelte-ignore a11y-missing-attribute -->
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->

        {#if hasCamera}
          <div
            class="action"
            on:click={handle_camera_off}
            use:click_outside={() => (cameraListShow = false)}
          >
            {#if cameraOff}
              <CameraOff></CameraOff>
            {:else}
              <CameraOn></CameraOn>
            {/if}

            {#if stream_state === "closed"}<div
                class="corner"
                on:click={open_camera_list}
              >
                <div class="corner-inner"></div>
              </div>{/if}
            <div
              class={`selectors ${actionsPosition.isOverflow || isSideBySide ? "left" : ""}`}
              style:display={cameraListShow && stream_state === "closed"
                ? "block"
                : "none"}
            >
              {#each available_video_devices as device, i}
                <div
                  class="selector"
                  on:click|stopPropagation={(e) =>
                    handle_device_change(device.deviceId)}
                >
                  {device.label}
                  {#if selected_video_device && device.deviceId === selected_video_device.deviceId}<div
                      class="active-icon"
                    >
                      <Check></Check>
                    </div>{/if}
                </div>
              {/each}
            </div>
          </div>
        {/if}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        {#if hasMic}
          <div
            class="action"
            on:click={handle_mic_mute}
            use:click_outside={() => (micListShow = false)}
          >
            {#if micMuted}
              <MicOff></MicOff>
            {:else}
              <MicOn></MicOn>
            {/if}

            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            {#if stream_state === "closed"}<div
                class="corner"
                on:click={open_mic_list}
              >
                <div class="corner-inner"></div>
              </div>{/if}
            <div
              class={`selectors ${actionsPosition.isOverflow || isSideBySide ? "left" : ""}`}
              style:display={micListShow && stream_state === "closed"
                ? "block"
                : "none"}
            >
              {#each available_audio_devices as device, i}
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <div
                  class="selector"
                  on:click|stopPropagation={(e) =>
                    handle_device_change(device.deviceId)}
                >
                  {device.label}
                  {#if selected_audio_device && device.deviceId === selected_audio_device.deviceId}
                    <div class="active-icon">
                      <Check></Check>
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        {/if}
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <div class="action" on:click={handle_volume_mute}>
          {#if volumeMuted}
            <VolumeOff></VolumeOff>
          {:else}
            <VolumeOn></VolumeOn>
          {/if}
        </div>
        {#if wrapperRect.width > 300}
        <div class="action" on:click={handle_subtitle_toggle}>
          {#if showChatRecords}
          <SubtitleOn></SubtitleOn>
          {:else}
          <SubtitleOff></SubtitleOff>
          {/if}
        </div>
        {/if}

      </div>
      {#if hasCamera}
        <div class="action-group">
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <div class="action" on:click={changeVideoShowType}>
            {#if isPictureInPicture}
              <PictureInPicture></PictureInPicture>
            {:else}
              <SideBySide></SideBySide>
            {/if}
          </div>
        </div>
      {/if}
    </div>
    

  </div>

  {#if (!hasMic || micMuted) && stream_state === "open"}
    <div
      class="chat-input-wrapper"
      class:side-by-side={isSideBySide}
      style={isPictureInPicture
        ? `left: ${chatInputPosition.left}px;width: ${chatInputPosition.width}px`
        : ""}
    >
      <ChatInput
        {replying}
        onInterrupt={on_interrupt}
        onSend={on_send}
        onStop={start_webrtc}
      ></ChatInput>
    </div>
  {:else}
    <ChatBtn
      onStartChat={start_webrtc}
      {audio_source_callback}
      {stream_state}
      {assetLoaded}
      {wave_color}
    ></ChatBtn>
  {/if}
</div>

<style lang="less">
  .wrap {
    background-image: url(./background.png);
    height: calc(max(80vh, 100%));
    position: relative;
    *::-webkit-scrollbar {
      display: none;
    }
    .chat-input-wrapper {
      position: absolute;
      transition: width 0.1s ease;
      &.side-by-side {
        left: 12px;
        right: 12px;
      }
    }

    .video-container {
      position: relative;
      height: 85%;
      padding-top: 24px;

      &.picture-in-picture {
        .local-video-container,
        .remote-video-container {
          position: absolute;
          top: 50%;
          left: 50%;
          width: 10px;
          height: 10px;
          border-radius: 32px;
          overflow: hidden;
          transition: all 0.3s linear;
          background: #fff;
        }
        .local-video-container {
          z-index: 1;
          background: #fff;
        }
        .local-video,
        .remote-video {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .chat-records-container{
          position: absolute;
          right: 12px;
          bottom: 0;
          height: 100%;
          overflow: auto;
          width: calc(50% - 32px);
          z-index: 1;
        }
        .remote-canvas {
          width: 100%;
          height: 100%;
        }
      }
      &.side-by-side {
        display: flex;
        justify-content: space-between;
        align-items: center;
        &.no-local-video {
          justify-content: center;
        }
        .local-video-container,
        .remote-video-container {
          position: static;
          width: 49%;
          height: 100%;
          flex-shrink: 0;
          flex-grow: 0;
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(20px);
          border-radius: 32px;
          transition: all 0.3s linear;
          overflow: hidden;
        }
        &.vertical {
          flex-direction: column-reverse;

          .local-video-container,
          .remote-video-container {
            width: 100%;
            height: 49%;
          }
        }
        .local-video,
        .remote-video {
          width: 100%;
          height: 100%;
          object-fit: contain;
        }

        .chat-records-container{
          position: absolute;
          right: 12px;
          bottom: 16px;
          width: 50%;
          z-index: 100;
          transform: translateZ(0);
        }
      }
      .actions {
        position: absolute;
        z-index: 2;
        left: calc(100% - 60px);
        .action-group {
          border-radius: 12px;
          background: rgba(88, 87, 87, 0.5);
          padding: 2px;
          backdrop-filter: blur(8px);
          .action {
            cursor: pointer;
            width: 42px;
            height: 42px;
            border-radius: 8px;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            color: #fff;

            .corner {
              position: absolute;
              right: 0px;
              bottom: 0px;
              padding: 3px;
              .corner-inner {
                width: 6px;
                height: 6px;
                border-top: 3px transparent solid;
                border-left: 3px transparent solid;
                border-bottom: 3px #fff solid;
                border-right: 3px #fff solid;
              }
            }
            // &:hover {
            // 	.selectors {
            // 		display: block !important;
            // 	}
            // }
            .selectors {
              position: absolute;
              top: 0;
              left: calc(100%);
              margin-left: 3px;
              max-height: 150px;

              &.left {
                left: 0;
                margin-left: -3px;
                transform: translateX(-100%);
              }
              border-radius: 12px;
              width: max-content;
              overflow: hidden;
              overflow: auto;

              background: rgba(90, 90, 90, 0.5);
              backdrop-filter: blur(8px);
              .selector {
                max-width: 250px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                position: relative;
                cursor: pointer;
                height: 42px;
                line-height: 42px;
                color: #fff;
                font-size: 14px;
                &:hover {
                  background: #67666a;
                }
                padding-left: 15px;
                padding-right: 50px;

                .active-icon {
                  position: absolute;
                  right: 10px;
                  width: 40px;
                  height: 40px;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  top: 0;
                }
              }
            }
          }
          .action:hover {
            background: #67666a;
          }
        }
        .action-group + .action-group {
          margin-top: 10px;
        }
      }
    }
  }
</style>
