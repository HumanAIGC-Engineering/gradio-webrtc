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
	export let show_local_video: boolean;
	export let i18n: I18nFormatter;

	let volumeMuted = false
	let micMuted = false
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
	 	<div class="video-wrap">
        	<video
            	bind:this={local_video_source}
            	class:hide={!webcam_accessed}
            	autoplay={true}
            	playsinline={true}
        	/>
        	<video
            	bind:this={video_source}
            	class:hide={!webcam_received}
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
					on:click={handle_mic_mute}
					aria-label="select input source"
				>
					{#if !micMuted}
					<svg t="1737450006667" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="12366" width="200" height="200"><path d="M285.216 562.9408a248.64 248.64 0 0 0 37.6448 59.7312 249.008 249.008 0 0 0 52.5056 46.64 245.5232 245.5232 0 0 0 64.0672 30.288c23.52 7.2032 47.712 10.8032 72.5664 10.8032 24.8544 0 49.0432-3.6 72.5664-10.8032a245.5296 245.5296 0 0 0 64.0672-30.288 248.896 248.896 0 0 0 52.5056-46.64 248.5888 248.5888 0 0 0 37.648-59.7312 32 32 0 1 1 58.4256 26.1184 312.2432 312.2432 0 0 1-47.2832 75.0336 312.6752 312.6752 0 0 1-65.936 58.5664 309.168 309.168 0 0 1-80.688 38.1376C573.6768 769.8688 543.2416 774.4 512 774.4c-31.2416 0-61.6768-4.5344-91.3056-13.6064a309.184 309.184 0 0 1-80.688-38.1376 312.6912 312.6912 0 0 1-65.936-58.5664 312.32 312.32 0 0 1-47.2832-75.0336 32 32 0 1 1 58.4256-26.1184z" p-id="12367"></path><path d="M339.4304 219.68a183.6896 183.6896 0 0 1 41.3312-62.9184 183.6896 183.6896 0 0 1 62.9184-41.3312A183.9712 183.9712 0 0 1 512 102.4a183.9712 183.9712 0 0 1 68.32 13.0304 183.6896 183.6896 0 0 1 62.9184 41.3312 183.696 183.696 0 0 1 41.3312 62.9184A183.9616 183.9616 0 0 1 697.6 288v198.4a183.952 183.952 0 0 1-13.0304 68.3168 183.7088 183.7088 0 0 1-41.3312 62.9216 183.6896 183.6896 0 0 1-62.9184 41.3312A183.9616 183.9616 0 0 1 512 672a183.9616 183.9616 0 0 1-68.32-13.0304 183.6896 183.6896 0 0 1-62.9184-41.3312 183.7024 183.7024 0 0 1-41.3312-62.9216A183.9616 183.9616 0 0 1 326.4 486.4V288a183.9712 183.9712 0 0 1 13.0304-68.32z m86.5856 352.704a120.3392 120.3392 0 0 0 41.2224 27.0784A120.512 120.512 0 0 0 512 608a120.512 120.512 0 0 0 44.7616-8.5376 120.3392 120.3392 0 0 0 41.2224-27.0784 120.3584 120.3584 0 0 0 27.0784-41.2224A120.544 120.544 0 0 0 633.6 486.4V288c0-15.4624-2.848-30.384-8.5376-44.7616a120.3552 120.3552 0 0 0-27.0784-41.2224 120.3552 120.3552 0 0 0-41.2224-27.0784A120.5344 120.5344 0 0 0 512 166.4c-15.4624 0-30.384 2.848-44.7616 8.5376a120.3552 120.3552 0 0 0-41.2224 27.0784 120.3552 120.3552 0 0 0-27.0784 41.2224A120.5312 120.5312 0 0 0 390.4 288v198.4c0 15.4624 2.848 30.384 8.5376 44.7616a120.3584 120.3584 0 0 0 27.0784 41.2224zM512 710.4c17.6736 0 32 14.3264 32 32v147.2c0 17.6736-14.3264 32-32 32s-32-14.3264-32-32v-147.2c0-17.6736 14.3264-32 32-32z" p-id="12368"></path><path d="M352 889.6c0-17.6736 14.3264-32 32-32h256c17.6736 0 32 14.3264 32 32s-14.3264 32-32 32h-256c-17.6736 0-32-14.3264-32-32z" p-id="12369"></path></svg>					
					{:else}
					<svg t="1737450020317" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="12521" width="200" height="200"><path d="M512 710.4c17.6736 0 32 14.3264 32 32v147.2c0 17.6736-14.3264 32-32 32s-32-14.3264-32-32v-147.2c0-17.6736 14.3264-32 32-32z" p-id="12522"></path><path d="M352 889.6c0-17.6736 14.3264-32 32-32h256c17.6736 0 32 14.3264 32 32s-14.3264 32-32 32h-256c-17.6736 0-32-14.3264-32-32zM217.3728 806.6272c-12.496-12.496-12.496-32.7584 0-45.2544L760.432 218.3136c12.496-12.496 32.7552-12.496 45.2544 0 12.496 12.4992 12.496 32.7584 0 45.2544L262.624 806.6272c-12.496 12.496-32.7584 12.496-45.2544 0zM414.8384 690.6208a246.336 246.336 0 0 0 24.5952 8.9792c23.52 7.2032 47.712 10.8032 72.5664 10.8032 24.8544 0 49.0432-3.6 72.5664-10.8032a245.5296 245.5296 0 0 0 64.0672-30.288 248.896 248.896 0 0 0 52.5056-46.64 248.5888 248.5888 0 0 0 37.648-59.7312 32 32 0 1 1 58.4256 26.1184 312.2432 312.2432 0 0 1-47.2832 75.0336 312.6752 312.6752 0 0 1-65.936 58.5664 309.168 309.168 0 0 1-80.688 38.1376C573.6768 769.8688 543.2416 774.4 512 774.4c-31.2416 0-61.6768-4.5344-91.3056-13.6064a308.7872 308.7872 0 0 1-53.8368-22.1984l47.9808-47.9776z m-140.768-26.528a312.32 312.32 0 0 1-47.2832-75.0336 32 32 0 1 1 58.4256-26.1184 248.544 248.544 0 0 0 36.2784 58.1088L276.096 666.4512c-0.6784-0.784-1.3504-1.568-2.0224-2.3584z" p-id="12523"></path><path d="M339.4304 219.68a183.6896 183.6896 0 0 1 41.3312-62.9184 183.6896 183.6896 0 0 1 62.9184-41.3312A183.9712 183.9712 0 0 1 512 102.4a183.9712 183.9712 0 0 1 68.32 13.0304 183.6896 183.6896 0 0 1 62.9184 41.3312 183.696 183.696 0 0 1 41.3312 62.9184 185.6512 185.6512 0 0 1 8.9248 29.3664L633.6 308.9408V288c0-15.4624-2.848-30.384-8.5376-44.7616a120.3552 120.3552 0 0 0-27.0784-41.2224 120.3552 120.3552 0 0 0-41.2224-27.0784A120.5344 120.5344 0 0 0 512 166.4c-15.4624 0-30.384 2.848-44.7616 8.5376a120.3552 120.3552 0 0 0-41.2224 27.0784 120.3552 120.3552 0 0 0-27.0784 41.2224A120.5312 120.5312 0 0 0 390.4 288v198.4c0 15.4624 2.848 30.384 8.5376 44.7616 1.1648 2.9472 2.432 5.824 3.8048 8.6368l-46.9344 46.9344a185.44 185.44 0 0 1-16.3776-32.016A183.9616 183.9616 0 0 1 326.4 486.4V288a183.9712 183.9712 0 0 1 13.0304-68.32zM697.6 486.4a183.952 183.952 0 0 1-13.0304 68.3168 183.7088 183.7088 0 0 1-41.3312 62.9216 183.6896 183.6896 0 0 1-62.9184 41.3312A183.9616 183.9616 0 0 1 512 672a183.872 183.872 0 0 1-66.2976-12.2432l52.5248-52.5248c4.544 0.512 9.1328 0.768 13.7728 0.768a120.512 120.512 0 0 0 44.7616-8.5376 120.3392 120.3392 0 0 0 41.2224-27.0784 120.3584 120.3584 0 0 0 27.0784-41.2224A120.544 120.544 0 0 0 633.6 486.4v-14.5408l64-64V486.4z" p-id="12524"></path></svg>					
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

	.hide {
		display: none;
	}

	.video-wrap {
        display: flex;
        justify-content: center;
        align-items: center;
    }

	video {
		width: var(--size-full);
		height: var(--size-full);
		object-fit: cover;
	}

	.video-wrap video {
		width: calc(50% - 3px);
		height: 50%;
		border-radius: var(--radius-sm);
	}
	.video-wrap video:last-child {
		margin-left: 6px;
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
		left: 100%;
		margin-left: 20px;
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