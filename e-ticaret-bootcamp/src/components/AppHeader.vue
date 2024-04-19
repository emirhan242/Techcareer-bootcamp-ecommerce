<template>
    <div class="appHeader">
        <div class="logo">Logo</div>
        <div class="box">
            <svg @click="onShow" viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
            <div class="badge" v-if="$store.getters.getBasketsLength!==0">{{  $store.getters.getBasketsLength}}</div>
            <ShopContext @goBasket="show=false" v-if="show"/>
        </div>
    </div>
</template>

<script>
    import ShopContext from './ShopContext.vue';

    export default {
        name: "AppHeader",
        components: {
            ShopContext
        },
        methods: {
            onShow() {
                this.show = !this.show;
            }
        },
        data() {
            return {
                show: false
            };
        }
    };
</script>


<style scoped>
    .appHeader{
        background: #fff;
        border-bottom: 1px solid #eff1f3;
        padding-left: 64px;
        padding-right: 64px;
        padding-top: 16px;
        padding-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .badge{
        display: flex;
        align-items: center;
        justify-content: center;
        width: 16px;
        height: 16px;
        color: #fff;
        border-radius: 100%;
        background-color: #1874ff;
        font-size: 10px;
        top: -8px;
        right: -8px;
        position: absolute;
    }

    .box{
        position: relative;
        cursor: pointer;
        color: #374051;
        transition: all .5s;
    }

    .box:hover{
        color: #1874ff;
    }

    .logo{
        cursor: pointer;
        font-weight: 600;
        font-size: 20px;
        letter-spacing: 12px;
        
    }
</style>