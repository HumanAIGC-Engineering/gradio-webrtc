<script lang="ts">
  import { Spinner } from "@gradio/icons";
  import AudioWave from "./AudioWave.svelte";
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  export let stream_state;
  export let onStartChat
  export let audio_source_callback
  export let wave_color
  export let assetLoaded = true
</script>

<div class="player-controls">
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="chat-btn"
    class:start-chat={stream_state === "closed"}
    class:stop-chat={stream_state === "open" && assetLoaded === true}
    on:click={onStartChat}
  >
    {#if stream_state === "closed"}
      <span>点击开始对话</span>
    {:else if stream_state === "waiting" || assetLoaded === false}
      <div class="waiting-icon-text">
        <div class="icon" title="spinner">
          <Spinner />
        </div>
        <span>等待中</span>
      </div>
    {:else}
      <div class="stop-chat-inner"></div>
    {/if}
  </div>
  {#if stream_state === "open" && assetLoaded === true}
  <div class="input-audio-wave">
    <AudioWave {audio_source_callback} {stream_state} {wave_color} />
  </div>
  {/if}
</div>

<style lang="less">
  .player-controls {
    height: 15%;
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 84px;

    .chat-btn {
      height: 64px;
      width: 296px;
      display: flex;
      justify-content: center;
      align-items: center;
      border-radius: 999px;
      opacity: 1;
      background: linear-gradient(180deg, #7873f6 0%, #524de1 100%);
      transition: all 0.3s;
      z-index: 2;
      cursor: pointer;
    }
    .start-chat {
      font-size: 16px;
      font-weight: 500;
      text-align: center;
      color: #ffffff;
    }
    .waiting-icon-text {
      width: 80px;
      align-items: center;
      font-size: 16px;
      font-weight: 500;
      color: #ffffff;
      margin: 0 var(--spacing-sm);
      display: flex;
      justify-content: space-evenly;
      gap: var(--size-1);
      .icon {
        width: 25px;
        height: 25px;
        fill: #ffffff;
        stroke: #ffffff;
        color: #ffffff;
      }
    }

    .stop-chat {
      width: 64px;
      .stop-chat-inner {
        width: 25px;
        height: 25px;
        border-radius: 6.25px;
        background: #fafafa;
      }
    }

    .input-audio-wave {
      position: absolute;
    }
  }
</style>
