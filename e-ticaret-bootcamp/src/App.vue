<template>
  <AppHeader />
  <AppContainer />
</template>

<script>
import AppHeader from './components/AppHeader.vue';
import AppContainer from './components/AppContainer.vue';

export default {
  name: 'App',
  components: {
    AppHeader,
    AppContainer
  }
}
</script>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
  body{
    margin: 0;
    color: #262B37;
    font-family: 'Poppins', sans-serif;
  }
</style>