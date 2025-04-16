<script lang="ts">
  export let message;
  export let style = "";
  export let role = "";

  $: classnames = `answer-message-container ${role}`
</script>

<div class={classnames} {style}>
  <div class="answer-message-text">
    {message}
  </div>
</div>

<style lang="less">
  .answer-message-container {
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.8);
    border-radius: 12px;
    color: #26244c;

    &.human {
      background: #dddddd99;
      // margin-left: 20px;
      margin-right: 0;
    }

    &.avatar {
      background: #9189fa;
      color: #ffffff;
      // margin-right: 20px;
    }
  }
</style>
