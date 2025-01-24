<script lang="ts">
	import { createEventDispatcher } from "svelte";
	import type { ComponentType } from "svelte";
	import type { FileData, Client } from "@gradio/client";

	import type { I18nFormatter } from "@gradio/utils";

	export let value: string = null;
	export let label: string | undefined = undefined;
	export let show_label = true;
	export let include_audio: boolean;
	export let show_local_video: string | undefined;
	export let i18n: I18nFormatter;
	export let active_source: "webcam" | "upload" = "webcam";
	export let handle_reset_value: () => void = () => {};
	export let stream_handler: Client["stream"];
	export let time_limit: number | null = null;
	export let button_labels: {start: string, stop: string, waiting: string};
	export let server: {
		offer: (body: any) => Promise<any>;
	};
	export let rtc_configuration: Object;
	export let track_constraints: MediaTrackConstraints = {};
	export let mode: "send" | "send-receive";
	export let on_change_cb: (msg: "change" | "tick") => void;
	export let rtp_params: RTCRtpParameters = {} as RTCRtpParameters;
	export let icon: string | undefined | ComponentType = undefined;
    export let icon_button_color: string = "var(--color-accent)";
    export let pulse_color: string = "var(--color-accent)";

	const dispatch = createEventDispatcher<{
		change: FileData | null;
		clear?: never;
		play?: never;
		pause?: never;
		end?: never;
		drag: boolean;
		error: string;
		upload: FileData;
		start_recording?: never;
		stop_recording?: never;
		tick: never;
	}>();

	let dragging = false;
	$: dispatch("drag", dragging);

	$: console.log("value", value)

</script>

<div>whatever i need</div>

<style>

</style>
