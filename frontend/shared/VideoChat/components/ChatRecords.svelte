<script lang="ts">
  import { tick } from "svelte";
  import ChatMessage from "./ChatMessage.svelte";

  export let chatRecords;

  let containerRef: HTMLElement
  $: if(chatRecords){
    tick().then(() => {
      scrollToBottom()
    })
  }
  function scrollToBottom() {
    // console.log("🚀 ~ scrollToBottom ~ scrollToBottom:")
    if(containerRef){
      containerRef.scrollTop = containerRef.scrollHeight;
    }
  }

  export const expose = { scrollToBottom };
</script>

<div class="chat-records" bind:this={containerRef}>
  <div class="chat-records-inner">
    {#each chatRecords as item, i (item.id)}
      <div class={`chat-message ${item.role}`}>
        <ChatMessage message={item.message} role={item.role}></ChatMessage>
      </div>
    {/each}
  </div>
</div>

<style lang="less">
  .chat-records{
    width: 100%;
    height: 100%;
    overflow-y: auto;
    &::-webkit-scrollbar {
      display: none;
    }
  }
  .chat-records-inner {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: end;
    width: 100%;
    // height: 100%;
    height: auto;
    min-height: 100%;
    .chat-message {
      margin-bottom: 12px;
      max-width: 80%;
      &.human {
        align-self: flex-end;
      }
      &.avatar {
        align-self: flex-start;
      }
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
</style>
