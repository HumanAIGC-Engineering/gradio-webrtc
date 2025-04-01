<script lang="ts">
  export let color;
  export let fontSize = "16px";
  export let icon: any = undefined;
</script>

<span style={`color: ${color}; font-size: ${fontSize}`}>
  {#if icon}
    <svelte:component this={icon} />
  {:else}
    <slot></slot>
  {/if}
</span>
