<script lang="ts">
  import { onDestroy } from "svelte";
  import type { ComponentType } from "svelte";

  import PulsingIcon from "../../PulsingIcon.svelte";

  export let numBars = 16;
  export let stream_state: "open" | "closed" | "waiting" = "closed";
  export let audio_source_callback: () => MediaStream;
  export let icon: string | undefined | ComponentType = undefined;
  export let icon_button_color: string = "var(--color-accent)";
  export let pulse_color: string = "var(--color-accent)";
  export let wave_color: string = "var(--color-accent)";

  let audioContext: AudioContext;
  let analyser: AnalyserNode;
  let dataArray: Uint8Array;
  let animationId: number;
  export let pulseScale = 1;

  $: containerWidth = icon
    ? "128px"
    : `calc((var(--boxSize) + var(--gutter)) * ${numBars} + 80px)`;

  $: if (stream_state === "open") setupAudioContext();

  onDestroy(() => {
    if (animationId) {
      cancelAnimationFrame(animationId);
    }
    if (audioContext) {
      audioContext.close();
    }
  });

  function setupAudioContext() {
    // @ts-ignore
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    const streamSource = audio_source_callback()
    if(!streamSource)return
    const source = audioContext.createMediaStreamSource(
      streamSource,
    );

    source.connect(analyser);

    analyser.fftSize = 64;
    analyser.smoothingTimeConstant = 0.8;
    dataArray = new Uint8Array(analyser.frequencyBinCount);

    updateVisualization();
  }

  function updateVisualization() {
    analyser.getByteFrequencyData(dataArray);
    
      // Update bars
      const bars = document.querySelectorAll('.gradio-webrtc-waveContainer .gradio-webrtc-box');
      for (let i = 0; i < bars.length; i++) {
        const barHeight = (dataArray[transformIndex(i)] / 255);
        bars[i].style.transform = `scaleY(${Math.max(0.1, barHeight)})`;
        bars[i].style.background = wave_color;
        bars[i].style.opacity = 0.5;
      }

    animationId = requestAnimationFrame(updateVisualization);
  }

  // 声波高度从两侧向中间收拢
  function transformIndex(index: number): number {
    const mapping = [0, 2, 4, 6, 8, 10, 12, 14, 15, 13, 11, 9, 7, 5, 3, 1];
    if (index < 0 || index >= mapping.length) {
        throw new Error("Index must be between 0 and 15");
    }
    return mapping[index];
}
</script>

<div class="gradio-webrtc-waveContainer">
  {#if icon && !pending}
    <div class="gradio-webrtc-icon-container">
      <div
        class="gradio-webrtc-icon"
        style:transform={`scale(${pulseScale})`}
        style:background={icon_button_color}
      >
        <PulsingIcon
          {stream_state}
          {pulse_color}
          {icon}
          {icon_button_color}
          {icon_radius}
          {audio_source_callback}
        />
      </div>
    </div>
{:else}
  <div class="gradio-webrtc-boxContainer" style:width={containerWidth}>
    {#each Array(numBars/2) as _}
      <div class="gradio-webrtc-box"></div>
    {/each}
    <div class="split-container"></div>
    {#each Array(numBars/2) as _}
      <div class="gradio-webrtc-box"></div>
    {/each}
  </div>
{/if}
</div>

<style>
  .gradio-webrtc-waveContainer {
    position: relative;
    display: flex;
    min-height: 100px;
    max-height: 128px;
    justify-content: center;
    align-items: center;
  }

.gradio-webrtc-boxContainer {
  display: flex;
  justify-content: space-between;
  height: 64px;
  --boxSize: 4px;
  --gutter: 4px;

}
.split-container {
    width: 80px;
  }
.gradio-webrtc-box {
  height: 100%;
  width: var(--boxSize);
  background: var(--color-accent);
  border-radius: 8px;
  transition: transform 0.05s ease;
}

  .gradio-webrtc-icon-container {
    position: relative;
    width: 128px;
    height: 128px;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .gradio-webrtc-icon {
    position: relative;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    transition: transform 0.1s ease;
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 2;
  }

  .icon-image {
    width: 32px;
    height: 32px;
    object-fit: contain;
    filter: brightness(0) invert(1);
  }

  .pulse-ring {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 48px;
    height: 48px;
    border-radius: 50%;
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    opacity: 0.5;
  }

  @keyframes pulse {
    0% {
      transform: translate(-50%, -50%) scale(1);
      opacity: 0.5;
    }
    100% {
      transform: translate(-50%, -50%) scale(var(--max-scale, 3));
      opacity: 0;
    }
  }

  .dots {
    display: flex;
    gap: 8px;
    align-items: center;
    height: 64px;
  }

  .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    opacity: 0.5;
    animation: pulse 1.5s infinite;
  }

  .dot:nth-child(2) {
    animation-delay: 0.2s;
  }

  .dot:nth-child(3) {
    animation-delay: 0.4s;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 0.4;
      transform: scale(1);
    }
    50% {
      opacity: 1;
      transform: scale(1.1);
    }
  }
</style>
