<svelte:options accessors={true} />

<script lang="ts">
	import { Block, UploadText } from "@gradio/atoms";
	import Video from "./shared/InteractiveVideo.svelte";
	import { StatusTracker } from "@gradio/statustracker";
	import type { LoadingStatus } from "@gradio/statustracker";
	import StaticVideo from "./shared/StaticVideo.svelte";
	import StaticAudio from "./shared/StaticAudio.svelte";
	import InteractiveAudio from "./shared/InteractiveAudio.svelte";
	import VideoChat from './shared/VideoChat.svelte'
	export let elem_id = "";
	export let elem_classes: string[] = [];
	export let visible = true;
	export let value: string = "__webrtc_value__";
	export let button_labels: {start: string, stop: string, waiting: string};

	export let label: string;
	export let root: string;
	export let show_label: boolean;
	export let loading_status: LoadingStatus;
	export let height: number | undefined;
	export let width: number | undefined;
	export let server: {
		offer: (body: any) => Promise<any>;
	};

	export let container = false;
	export let scale: number | null = null;
	export let min_width: number | undefined = undefined;
	export let gradio;
	export let rtc_configuration: Object;
	export let time_limit: number | null = null;
	export let modality: "video" | "audio" | "audio-video" = "video";
	export let mode: "send-receive" | "receive" | "send" = "send-receive";
	export let show_local_video: string | undefined = undefined;
	export let video_chat: boolean = false;
	export let rtp_params: RTCRtpParameters = {} as RTCRtpParameters;
	export let track_constraints: MediaTrackConstraints = {};
	export let icon: string | undefined = undefined;
	export let icon_button_color: string = "var(--color-accent)";
	export let pulse_color: string = "var(--color-accent)";

	const on_change_cb = (msg: "change" | "tick" | any) => {
		if (msg?.type === "info" || msg?.type === "warning" || msg?.type === "error") {
			console.log("dispatching info", msg.message);
			gradio.dispatch(msg?.type === "error"? "error": "warning", msg.message);
		}
		gradio.dispatch(msg === "change" ? "state_change" : "tick");
	}

	let dragging = false;

	$: console.log("value", value);
</script>

{#if video_chat}
	<Block
	{visible}
	variant={"solid"}
	border_mode={dragging ? "focus" : "base"}
	padding={false}
	{elem_id}
	{elem_classes}
	{height}
	{width}
	{container}
	{scale}
	{min_width}
	allow_overflow={false}>
		<VideoChat {server} bind:webrtc_id={value}
		on:clear={() => gradio.dispatch("clear")}
		on:play={() => gradio.dispatch("play")}
		on:pause={() => gradio.dispatch("pause")}
		on:upload={() => gradio.dispatch("upload")}
		on:stop={() => gradio.dispatch("stop")}
		on:end={() => gradio.dispatch("end")}
		on:start_recording={() => gradio.dispatch("start_recording")}
		on:stop_recording={() => gradio.dispatch("stop_recording")}
		on:tick={() => gradio.dispatch("tick")}
		on:error={({ detail }) => gradio.dispatch("error", detail)}
		i18n={gradio.i18n}
		stream_handler={(...args) => gradio.client.stream(...args)}
		{track_constraints}
		{height}
		{on_change_cb} {rtc_configuration}
		on:tick={() => gradio.dispatch("tick")}
		on:error={({ detail }) => gradio.dispatch("error", detail)}></VideoChat>
	</Block>

{:else}<Block
	{visible}
	variant={"solid"}
	border_mode={dragging ? "focus" : "base"}
	padding={false}
	{elem_id}
	{elem_classes}
	{height}
	{width}
	{container}
	{scale}
	{min_width}
	allow_overflow={false}
	>
		<StatusTracker
			autoscroll={gradio.autoscroll}
			i18n={gradio.i18n}
			{...loading_status}
			on:clear_status={() => gradio.dispatch("clear_status", loading_status)}
		/>

	{#if mode == "receive" && modality === "video"}
		<StaticVideo
			bind:value={value}
			{on_change_cb}
			{label}
			{show_label}
			{server}
			{rtc_configuration}
			on:tick={() => gradio.dispatch("tick")}
			on:error={({ detail }) => gradio.dispatch("error", detail)}
		/>
	{:else if mode == "receive" && modality === "audio"}
		<StaticAudio
			bind:value={value}
			{on_change_cb}
			{label}
			{show_label}
			{server}
			{rtc_configuration}
			{icon}
			{icon_button_color}
			{pulse_color}
			i18n={gradio.i18n}
			on:tick={() => gradio.dispatch("tick")}
			on:error={({ detail }) => gradio.dispatch("error", detail)}

		/>
	{:else if (mode === "send-receive" || mode == "send") && (modality === "video" || modality == "audio-video")}
		<Video
			bind:value={value}
			{label}
			{show_label}
			active_source={"webcam"}
			include_audio={modality === "audio-video"}
			show_local_video={mode === "send-receive" && modality === "audio-video" && show_local_video}
			{server}
			{rtc_configuration}
			{time_limit}
			{mode}
			{track_constraints}
			{rtp_params}
			{on_change_cb}
			{icon}
			{icon_button_color}
			{pulse_color}
			{button_labels}
			on:clear={() => gradio.dispatch("clear")}
			on:play={() => gradio.dispatch("play")}
			on:pause={() => gradio.dispatch("pause")}
			on:upload={() => gradio.dispatch("upload")}
			on:stop={() => gradio.dispatch("stop")}
			on:end={() => gradio.dispatch("end")}
			on:start_recording={() => gradio.dispatch("start_recording")}
			on:stop_recording={() => gradio.dispatch("stop_recording")}
			on:tick={() => gradio.dispatch("tick")}
			on:error={({ detail }) => gradio.dispatch("error", detail)}
			i18n={gradio.i18n}
			stream_handler={(...args) => gradio.client.stream(...args)}
		>
			<UploadText i18n={gradio.i18n} type="video" />
		</Video>
	{:else if (mode === "send-receive" || mode === "send") && modality === "audio"}
		<InteractiveAudio
			bind:value={value}
			{on_change_cb}
			{label}
			{show_label}
			{server}
			{rtc_configuration}
			{time_limit}
			{track_constraints}
			{mode}
			{rtp_params}
			i18n={gradio.i18n}
			{icon}
			{icon_button_color}
			{pulse_color}
			{button_labels}
			on:tick={() => gradio.dispatch("tick")}
			on:error={({ detail }) => gradio.dispatch("error", detail)}
			on:warning={({ detail }) => gradio.dispatch("warning", detail)}
		/>
	{/if}
</Block>
{/if}
