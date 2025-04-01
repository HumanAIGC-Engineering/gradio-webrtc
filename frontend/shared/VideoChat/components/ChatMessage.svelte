<script lang="ts">
  export let message;
  export let style = '';
</script>

<div
  class="answer-message-container"
  {style}
>
  <div class="answer-message-text">
    {message}
  </div>
</div>

<style lang="less">
  .answer-message-container {
    position: absolute;
    right: 12px;
    z-index: 101;
    padding: 6px 12px;
    border-radius: 12px;
    width: 200px;
    background: rgba(255, 255, 255, 0.8);
    bottom: 166px;
  }
</style>
