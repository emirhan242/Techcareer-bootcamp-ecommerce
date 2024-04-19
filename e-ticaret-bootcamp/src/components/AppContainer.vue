<template>
    <div class="app-container">
        <RouterView />
    </div>
</template>

<script>
import { RouterView } from 'vue-router';

export default {
  name: 'AppContainer',
  components: {
    RouterView
  }
}
</script>

<style scoped>
    .app-container{
        padding: 64px;
    }
</style>