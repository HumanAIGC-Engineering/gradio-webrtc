<script lang="ts">
	import { createEventDispatcher, onMount } from "svelte";
	import type { ComponentType } from "svelte";
	import {
		Circle,
		Square,
		DropdownArrow,
		Spinner,
		Microphone as Mic,
		VolumeMuted,
		Webcam,
		VolumeHigh
	} from "@gradio/icons";
	import type { I18nFormatter } from "@gradio/utils";
	import { StreamingBar } from "@gradio/statustracker";
	import WebcamPermissions from "./WebcamPermissions.svelte";
	import { fade } from "svelte/transition";
	import {
		get_devices,
		get_video_stream,
		set_available_devices
	} from "./stream_utils";
    import { start, stop } from "./webrtc_utils";
    import PulsingIcon from "./PulsingIcon.svelte";

	let local_video_source: HTMLVideoElement;
	let video_source: HTMLVideoElement;
	let available_video_devices: MediaDeviceInfo[] = [];
	let available_audio_devices: MediaDeviceInfo[] = [];
	let selected_device: MediaDeviceInfo | null = null;
	let selected_audio_device: MediaDeviceInfo | null = null;
	let _time_limit: number | null = null;
    export let time_limit: number | null = null;
	let stream_state: "open" | "waiting" | "closed" = "closed";
	export let on_change_cb: (msg: "tick" | "change") => void;
	export let mode: "send-receive" | "send";
    const _webrtc_id = Math.random().toString(36).substring(2);
	export let rtp_params: RTCRtpParameters = {} as RTCRtpParameters;
	export let icon: string | undefined | ComponentType = undefined;
    export let icon_button_color: string = "var(--color-accent)";
    export let pulse_color: string = "var(--color-accent)";
	export let button_labels: {start: string, stop: string, waiting: string};

	export const modify_stream: (state: "open" | "closed" | "waiting") => void = (
		state: "open" | "closed" | "waiting"
	) => {
		if (state === "closed") {
			_time_limit = null;
			stream_state = "closed";
		} else if (state === "waiting") {
			stream_state = "waiting";
		} else {
			stream_state = "open";
		}
	};

	let canvas: HTMLCanvasElement;
	export let track_constraints: MediaTrackConstraints | null = null;
    export let rtc_configuration: Object;
	export let stream_every = 1;
	export let server: {
		offer: (body: any) => Promise<any>;
	};

	export let include_audio: boolean;
	export let show_local_video: string | undefined;
	export let i18n: I18nFormatter;

	let volumeMuted = false
	let micMuted = false
	let cameraOff = false
	const handle_volume_mute = () => {
		volumeMuted = !volumeMuted
	}
	const handle_mic_mute = () => {
		micMuted = !micMuted
		stream.getTracks().forEach(track => {
			if (track.kind.includes('audio'))
			track.enabled = !micMuted
		})
	}
	const handle_camera_off = () => {
		cameraOff = !cameraOff
		stream.getTracks().forEach(track => {
			if (track.kind.includes('video'))
			track.enabled = !cameraOff
		})

	}
	

	const dispatch = createEventDispatcher<{
		tick: undefined;
		error: string;
		start_recording: undefined;
		stop_recording: undefined;
		close_stream: undefined;
	}>();

	onMount(() => (canvas = document.createElement("canvas")));

	const handle_device_change = async (event: InputEvent): Promise<void> => {
		const target = event.target as HTMLInputElement;
		const device_id = target.value;
		let videoDeviceId
		let audioDeviceId
		if (include_audio && available_audio_devices.find(audio_device => audio_device.deviceId === device_id)) {
			audioDeviceId = device_id
		} else {
			videoDeviceId = device_id
		}
		const node = show_local_video ? local_video_source : video_source; 
		await get_video_stream(audioDeviceId ? {
				deviceId: { exact: audioDeviceId },
		}: include_audio, node, videoDeviceId, track_constraints).then(

			async (local_stream) => {
				stream = local_stream;
				selected_device =
					available_video_devices.find(
						(device) => device.deviceId === videoDeviceId
					) || null;
				selected_audio_device = include_audio ?
					available_audio_devices.find(
						(device) => device.deviceId === audioDeviceId
					) || null
					: null;
				options_open = false;
			}
		);
	};

	async function access_webcam(): Promise<void> {
		try {
			const node = show_local_video ? local_video_source : video_source; 
			micMuted = false
			cameraOff = false
			volumeMuted = false
			get_video_stream(include_audio, node, null, track_constraints)
				.then(async (local_stream) => {
					webcam_accessed = true;
					let available_devices = await get_devices();
					stream = local_stream;
					return available_devices
				})
				// .then(() => set_available_devices(available_video_devices))
				.then((devices) => {
					available_video_devices = set_available_devices(devices, "videoinput");
					available_audio_devices = set_available_devices(devices, "audioinput");

					const used_devices = stream
						.getTracks()
						.map((track) => track.getSettings()?.deviceId);
					used_devices.forEach((device_id) => {
						const used_device = devices.find(
							(device) => device.deviceId === device_id
						);
						if (used_device && used_device?.kind.includes('video')) {
							selected_device = used_device;
						} else if (used_device && used_device?.kind.includes('audio')) {
							selected_audio_device = used_device;
						}
					});
					!selected_device && (selected_device = available_video_devices[0])
				});

			if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
				dispatch("error", i18n("image.no_webcam_support"));
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

	let webcam_accessed = false;
	let webcam_received = false;
    let pc: RTCPeerConnection;
	export let webrtc_id;

	async function start_webrtc(): Promise<void> {
        if (stream_state === 'closed') {
            pc = new RTCPeerConnection(rtc_configuration);
            pc.addEventListener("connectionstatechange",
                async (event) => {
                   switch(pc.connectionState) {
                        case "connected":
                            stream_state = "open";
                            _time_limit = time_limit;
                            break;
                        case "disconnected":
                            stream_state = "closed";
							_time_limit = null;
							stop(pc);
                            await access_webcam();
                            break;
                        default:
                            break;
                   }
                }
            )
            stream_state = "waiting"
			webrtc_id = Math.random().toString(36).substring(2);
            start(stream, pc, mode === "send" ? null: video_source, server.offer, webrtc_id, "video", on_change_cb, rtp_params).then((connection) => {
				pc = connection;
				webcam_received = true;
			}).catch(() => {
                console.info("catching")
                stream_state = "closed";
				webcam_received = false;
                dispatch("error", "Too many concurrent users. Come back later!");
            });
        } else {
            stop(pc);
            stream_state = "closed";
			webcam_received = false;
			_time_limit = null;
            await access_webcam();
        }
	}

	let options_open = false;

	export function click_outside(node: Node, cb: any): any {
		const handle_click = (event: MouseEvent): void => {
			if (
				node &&
				!node.contains(event.target as Node) &&
				!event.defaultPrevented
			) {
				cb(event);
			}
		};

		document.addEventListener("click", handle_click, true);

		return {
			destroy() {
				document.removeEventListener("click", handle_click, true);
			}
		};
	}

	function handle_click_outside(event: MouseEvent): void {
		event.preventDefault();
		event.stopPropagation();
		options_open = false;
	}

	const audio_source_callback = () => video_source.srcObject as MediaStream;
</script>

<div class="wrap">
	<StreamingBar time_limit={_time_limit} />
	{#if stream_state === "open" && include_audio}
		<div class="audio-indicator">
			<PulsingIcon
				stream_state={stream_state}
				audio_source_callback={audio_source_callback}
				icon={icon || Mic}
				icon_button_color={icon_button_color}
				pulse_color={pulse_color}
			/>
		</div>
	{/if}
	<!-- svelte-ignore a11y-media-has-caption -->
	<!-- need to suppress for video streaming https://github.com/sveltejs/svelte/issues/5967 -->
	 {#if show_local_video}
	 	<div class="video-wrap"  class:picinpic={show_local_video === 'picture-in-picture'} class:left-right={show_local_video === 'left-right'} class:hide={!webcam_accessed}>
        	<video
							class:local-video={stream_state === "open"}
							class:remote-video={stream_state !== "open"}
            	bind:this={local_video_source}
            	class:hide={!webcam_accessed || cameraOff}
            	autoplay={true}
            	playsinline={true}
							muted
        	/>
        	<video
							class="remote-video"
            	bind:this={video_source}
            	class:hide={!webcam_received || stream_state != "open"}
            	class:flip={stream_state != "open" ||
                	(stream_state === "open" && include_audio)}
            	autoplay={true}
							muted={volumeMuted}
            	playsinline={true}
        	/>
    	</div>
	 {:else}
	 	<video
	 		bind:this={video_source}
	 		class:hide={!webcam_accessed}
	 		class:flip={(stream_state != "open") || (stream_state === "open" && include_audio)}
	 		autoplay={true}
			muted={volumeMuted}
	 		playsinline={true}
 		/>
	 {/if}
	

	<!-- svelte-ignore a11y-missing-attribute -->
	{#if !webcam_accessed}
		<div
			in:fade={{ delay: 100, duration: 200 }}
			title="grant webcam access"
			style="height: 100%"
		>
			<WebcamPermissions on:click={async () => access_webcam()} />
		</div>
	{:else}
		<div class="button-wrap">
			<button
				on:click={start_webrtc}
				aria-label={"start stream"}
			>
                {#if stream_state === "waiting"}
                    <div class="icon-with-text">
                        <div class="icon color-primary" title="spinner">
                            <Spinner />
                        </div>
                        {button_labels.waiting || i18n("audio.waiting")}
                    </div>
                {:else if stream_state === "open"}
                    <div class="icon-with-text">
                        <div class="icon color-primary" title="stop recording">
                            <Square />
                        </div>
                        {button_labels.stop || i18n("audio.stop")}
                    </div>
                {:else}
                    <div class="icon-with-text">
                        <div class="icon color-primary" title="start recording">
                            <Circle />
                        </div>
                        {button_labels.start || i18n("audio.record")}
                    </div>
                {/if}
			</button>
			{#if !recording}
				<button
					class="icon"
					on:click={() => (options_open = true)}
					aria-label="select input source"
				>
					<DropdownArrow />
				</button>
			{/if}
			{#if include_audio === true && stream_state === "open"}
			<div class="action-wrap">
				<button
					class="icon"
					on:click={handle_camera_off}
					aria-label="select input source"
				>
					{#if !cameraOff}
					<svg viewBox="64 64 896 896" focusable="false" data-icon="camera" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="M864 248H728l-32.4-90.8a32.07 32.07 0 00-30.2-21.2H358.6c-13.5 0-25.6 8.5-30.1 21.2L296 248H160c-44.2 0-80 35.8-80 80v456c0 44.2 35.8 80 80 80h704c44.2 0 80-35.8 80-80V328c0-44.2-35.8-80-80-80zm8 536c0 4.4-3.6 8-8 8H160c-4.4 0-8-3.6-8-8V328c0-4.4 3.6-8 8-8h186.7l17.1-47.8 22.9-64.2h250.5l22.9 64.2 17.1 47.8H864c4.4 0 8 3.6 8 8v456zM512 384c-88.4 0-160 71.6-160 160s71.6 160 160 160 160-71.6 160-160-71.6-160-160-160zm0 256c-53 0-96-43-96-96s43-96 96-96 96 43 96 96-43 96-96 96z"></path></svg>
					{:else}
					<svg viewBox="64 64 896 896" focusable="false" data-icon="camera" width="1em" height="1em" fill="currentColor" aria-hidden="true">  <line fill="none" id="svg_5" stroke="#000000" stroke-width="80" x1="860" x2="100" y1="100" y2="860"/><path d="M864 248H728l-32.4-90.8a32.07 32.07 0 00-30.2-21.2H358.6c-13.5 0-25.6 8.5-30.1 21.2L296 248H160c-44.2 0-80 35.8-80 80v456c0 44.2 35.8 80 80 80h704c44.2 0 80-35.8 80-80V328c0-44.2-35.8-80-80-80zm8 536c0 4.4-3.6 8-8 8H160c-4.4 0-8-3.6-8-8V328c0-4.4 3.6-8 8-8h186.7l17.1-47.8 22.9-64.2h250.5l22.9 64.2 17.1 47.8H864c4.4 0 8 3.6 8 8v456zM512 384c-88.4 0-160 71.6-160 160s71.6 160 160 160 160-71.6 160-160-71.6-160-160-160zm0 256c-53 0-96-43-96-96s43-96 96-96 96 43 96 96-43 96-96 96z"></path></svg>
					{/if}
				</button>
				<button
					class="icon"
					on:click={handle_mic_mute}
					aria-label="select input source"
				>
					{#if !micMuted}
					<svg viewBox="64 64 896 896" focusable="false" data-icon="audio" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="M842 454c0-4.4-3.6-8-8-8h-60c-4.4 0-8 3.6-8 8 0 140.3-113.7 254-254 254S258 594.3 258 454c0-4.4-3.6-8-8-8h-60c-4.4 0-8 3.6-8 8 0 168.7 126.6 307.9 290 327.6V884H326.7c-13.7 0-24.7 14.3-24.7 32v36c0 4.4 2.8 8 6.2 8h407.6c3.4 0 6.2-3.6 6.2-8v-36c0-17.7-11-32-24.7-32H548V782.1c165.3-18 294-158 294-328.1zM512 624c93.9 0 170-75.2 170-168V232c0-92.8-76.1-168-170-168s-170 75.2-170 168v224c0 92.8 76.1 168 170 168zm-94-392c0-50.6 41.9-92 94-92s94 41.4 94 92v224c0 50.6-41.9 92-94 92s-94-41.4-94-92V232z"></path></svg>					
					{:else}
					<svg viewBox="64 64 896 896" focusable="false" data-icon="audio-muted" width="1em" height="1em" fill="currentColor" aria-hidden="true"><defs><style></style></defs><path d="M682 455V311l-76 76v68c-.1 50.7-42 92.1-94 92a95.8 95.8 0 01-52-15l-54 55c29.1 22.4 65.9 36 106 36 93.8 0 170-75.1 170-168z"></path><path d="M833 446h-60c-4.4 0-8 3.6-8 8 0 140.3-113.7 254-254 254-63 0-120.7-23-165-61l-54 54a334.01 334.01 0 00179 81v102H326c-13.9 0-24.9 14.3-25 32v36c.1 4.4 2.9 8 6 8h408c3.2 0 6-3.6 6-8v-36c0-17.7-11-32-25-32H547V782c165.3-17.9 294-157.9 294-328 0-4.4-3.6-8-8-8zm13.1-377.7l-43.5-41.9a8 8 0 00-11.2.1l-129 129C634.3 101.2 577 64 511 64c-93.9 0-170 75.3-170 168v224c0 6.7.4 13.3 1.2 19.8l-68 68A252.33 252.33 0 01258 454c-.2-4.4-3.8-8-8-8h-60c-4.4 0-8 3.6-8 8 0 53 12.5 103 34.6 147.4l-137 137a8.03 8.03 0 000 11.3l42.7 42.7c3.1 3.1 8.2 3.1 11.3 0L846.2 79.8l.1-.1c3.1-3.2 3-8.3-.2-11.4zM417 401V232c0-50.6 41.9-92 94-92 46 0 84.1 32.3 92.3 74.7L417 401z"></path></svg>					
					{/if}
				</button>
				<button
					class="icon"
					on:click={handle_volume_mute}
					aria-label="select input source"
				>
					{#if volumeMuted}
					<VolumeMuted/>
					{:else}
					<VolumeHigh/>
					{/if}
				</button>
			</div>
	
			{/if}
		</div>

		{#if options_open && selected_device}
			<div
				class="select-container"
				use:click_outside={handle_click_outside}
			>
				<select
					class="select-wrap"
					aria-label="select source"
					on:change={handle_device_change}
				>
					<button
						class="inset-icon"
						on:click|stopPropagation={() => (options_open = false)}
					>
						<DropdownArrow />
					</button>
					{#if available_video_devices.length === 0}
						<option value="">{i18n("common.no_devices")}</option>
					{:else}
						{#each available_video_devices as device}
							<option
								value={device.deviceId}
								selected={selected_device.deviceId === device.deviceId}
							>
								{device.label}
							</option>
						{/each}
					{/if}
				</select>
				{#if include_audio=== true}
				<select
					class="select-wrap"
					aria-label="select source"
					on:change={handle_device_change}
				>
					<button
						class="inset-icon"
						on:click|stopPropagation={() => (options_open = false)}
					>
						<DropdownArrow />
					</button>
					{#if available_audio_devices.length === 0}
						<option value="">{i18n("common.no_devices")}</option>
					{:else}
						{#each available_audio_devices as device}
							<option
								value={device.deviceId}
								selected={selected_audio_device.deviceId === device.deviceId}
							>
								{device.label}
							</option>
						{/each}
					{/if}
				</select>
				{/if}
			</div>

		{/if}
	{/if}
</div>

<style>
	.wrap {
		position: relative;
		width: var(--size-full);
		height: var(--size-full);
	}



	.video-wrap {
		height: 100%;
		width: 100%;
		position: relative;
		display: flex;
		justify-content: center;
		align-items: center;
  }
	.hide {
		display: none;
	}

	video {
		width: var(--size-full);
		height: var(--size-full);
		object-fit: cover;
	}

	.video-wrap.left-right video {
		width: calc(50% - 3px);
		height: 100%;
		border-radius: var(--radius-sm);
	}
	.video-wrap.left-right video:last-child {
		margin-left: 6px;
	}
	.video-wrap.picinpic .remote-video {
		width: var(--size-full);
		height: var(--size-full);
		object-fit: contain;
	}
	.video-wrap.picinpic .local-video {
		position:absolute;
		left: 5%;
		bottom: 15%;
		/* width: 20%; */
		object-fit: contain;
		object-position: left;
		height: 20%;
		z-index: 1;
	}

	.button-wrap {
		position: absolute;
		background-color: var(--block-background-fill);
		border: 1px solid var(--border-color-primary);
		border-radius: var(--radius-xl);
		padding: var(--size-1-5);
		display: flex;
		bottom: var(--size-2);
		left: 50%;
		transform: translate(-50%, 0);
		box-shadow: var(--shadow-drop-lg);
		border-radius: var(--radius-xl);
		line-height: var(--size-3);
		color: var(--button-secondary-text-color);
	}

	.action-wrap {
		position: absolute;
		right: 100%;
		margin-right: 20px;
		top: 0;
		background-color: var(--block-background-fill);
		border: 1px solid var(--border-color-primary);
		border-radius: var(--radius-xl);
		padding: var(--size-1-5);
		display: flex;
		box-shadow: var(--shadow-drop-lg);
		border-radius: var(--radius-xl);
		line-height: var(--size-3);
		color: var(--button-secondary-text-color);
	}
	.action-wrap .icon+.icon {
		margin-left: 10px;
	}

	.icon-with-text {
		min-width: var(--size-16);
		align-items: center;
		margin: 0 var(--spacing-xl);
		display: flex;
        justify-content: space-evenly;    
        /* Add gap between icon and text */
        gap: var(--size-2);
	}

    .audio-indicator {
        position: absolute;
        top: var(--size-2);
        right: var(--size-2);
		z-index: var(--layer-2);
		height: var(--size-5);
		width: var(--size-5);
    }

	@media (--screen-md) {
		button {
			bottom: var(--size-4);
		}
	}

	@media (--screen-xl) {
		button {
			bottom: var(--size-8);
		}
	}

	.icon {
		width: 18px;
		height: 18px;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.color-primary {
		fill: var(--primary-600);
		stroke: var(--primary-600);
		color: var(--primary-600);
	}

	.flip {
		transform: scaleX(-1);
	}
	.select-container {
		width: 95%;
		left: 50%;
		text-align: center;
		transform: translate(-50%, 0);
		position: absolute;
		bottom: var(--size-2);
	}
	.select-wrap {
		-webkit-appearance: none;
		-moz-appearance: none;
		appearance: none;
		color: var(--button-secondary-text-color);
		background-color: transparent;
		
		font-size: var(--text-md);

		background-color: var(--block-background-fill);
		box-shadow: var(--shadow-drop-lg);
		border-radius: var(--radius-xl);
		z-index: var(--layer-top);
		border: 1px solid var(--border-color-primary);
		text-align: left;
		line-height: var(--size-4);
		white-space: nowrap;
		text-overflow: ellipsis;
		max-width: var(--size-52);
	}

	.select-wrap > option {
		padding: 0.25rem 0.5rem;
		border-bottom: 1px solid var(--border-color-accent);
		padding-right: var(--size-8);
		text-overflow: ellipsis;
		overflow: hidden;
	}

	.select-wrap > option:hover {
		background-color: var(--color-accent);
	}

	.select-wrap > option:last-child {
		border: none;
	}

	.inset-icon {
		position: absolute;
		top: 5px;
		right: -6.5px;
		width: var(--size-10);
		height: var(--size-5);
		opacity: 0.8;
	}

	@media (--screen-md) {
		.wrap {
			font-size: var(--text-lg);
		}
	}
</style>